package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigModel
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigProvider
import com.jarvis.chat.feature.ai.domain.model.DeepSeekModelProvider
import com.jarvis.chat.feature.ai.domain.model.DeepSeekPromptConfigModel
import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.client.engine.mock.respondError
import io.ktor.client.plugins.ClientRequestException
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.HttpRequestData
import io.ktor.http.ContentType
import io.ktor.http.HttpStatusCode
import io.ktor.http.content.TextContent
import io.ktor.http.headersOf
import io.ktor.http.HttpHeaders
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

private const val TEST_MAX_TOKENS = 900
private const val TEST_TEMPERATURE = 0.6
private const val TEST_REPETITION_PENALTY = 1.1

class DeepSeekRemoteDataSourceImplTest {

    @Test
    fun requestCompletion_postsToCompletionsPath() = runTest {
        val captured = mutableListOf<HttpRequestData>()
        val dataSource = dataSourceReturning(body = successBody("hi"), captured = captured)

        dataSource.requestCompletion(listOf(userMessage("hello")))

        assertEquals("/chat/completions", captured.single().url.encodedPath)
    }

    @Test
    fun requestCompletion_prependsSystemPromptBeforeHistory() = runTest {
        val captured = mutableListOf<HttpRequestData>()
        val dataSource = dataSourceReturning(body = successBody("hi"), captured = captured)

        dataSource.requestCompletion(listOf(userMessage("hello")))

        val sentBody = (captured.single().body as TextContent).text
        val roles = Regex("\"role\":\"(\\w+)\"").findAll(sentBody).map { match -> match.groupValues[1] }.toList()
        assertEquals(listOf("system", "user"), roles)
        assertTrue(
            sentBody.contains("\"content\":\"${testPromptConfig.systemPrompt}\""),
            "system prompt from config missing in: $sentBody",
        )
    }

    @Test
    fun requestCompletion_disablesStreaming() = runTest {
        val captured = mutableListOf<HttpRequestData>()
        val dataSource = dataSourceReturning(body = successBody("hi"), captured = captured)

        dataSource.requestCompletion(listOf(userMessage("hello")))

        val sentBody = (captured.single().body as TextContent).text
        assertTrue(sentBody.contains("\"stream\":false"), "stream flag missing in: $sentBody")
    }

    @Test
    fun requestCompletion_sendsModelFromProvider() = runTest {
        val captured = mutableListOf<HttpRequestData>()
        val dataSource = dataSourceReturning(body = successBody("hi"), captured = captured)

        dataSource.requestCompletion(listOf(userMessage("hello")))

        val sentBody = (captured.single().body as TextContent).text
        assertTrue(
            sentBody.contains("\"model\":\"${testModelProvider.currentModel()}\""),
            "model missing in: $sentBody",
        )
    }

    @Test
    fun requestCompletion_readsModelFromProviderOnEveryCall() = runTest {
        val captured = mutableListOf<HttpRequestData>()
        var currentModel = "model-a"
        val dataSource = dataSourceReturning(
            body = successBody("hi"),
            captured = captured,
            modelProvider = DeepSeekModelProvider { currentModel },
        )

        dataSource.requestCompletion(listOf(userMessage("hello")))
        currentModel = "model-b"
        dataSource.requestCompletion(listOf(userMessage("hello again")))

        val sentBodies = captured.map { request -> (request.body as TextContent).text }
        assertTrue(sentBodies[0].contains("\"model\":\"model-a\""), "first request missing model-a in: ${sentBodies[0]}")
        assertTrue(sentBodies[1].contains("\"model\":\"model-b\""), "second request missing model-b in: ${sentBodies[1]}")
    }

    @Test
    fun requestCompletion_parsesAssistantContentFromResponse() = runTest {
        val dataSource = dataSourceReturning(body = successBody("Privet"))

        val response = dataSource.requestCompletion(listOf(userMessage("hello")))

        assertEquals("Privet", response.choices.single().message.content)
        assertEquals("assistant", response.choices.single().message.role)
    }

    @Test
    fun requestCompletion_ignoresUnknownFieldsInResponse() = runTest {
        val body = """
            {"id":"abc","object":"chat.completion","usage":{"total_tokens":7},
             "choices":[{"index":0,"finish_reason":"stop",
             "message":{"role":"assistant","content":"ok"}}]}
        """.trimIndent()
        val dataSource = dataSourceReturning(body = body)

        val response = dataSource.requestCompletion(listOf(userMessage("hello")))

        assertEquals("ok", response.choices.single().message.content)
    }

    @Test
    fun requestCompletion_omitsGenerationParamsWhenProviderDoesNotSetThem() = runTest {
        val captured = mutableListOf<HttpRequestData>()
        val dataSource = dataSourceReturning(body = successBody("hi"), captured = captured)

        dataSource.requestCompletion(listOf(userMessage("hello")))

        val sentBody = (captured.single().body as TextContent).text
        assertTrue(!sentBody.contains("max_tokens"), "max_tokens must be absent in: $sentBody")
        assertTrue(!sentBody.contains("temperature"), "temperature must be absent in: $sentBody")
        assertTrue(!sentBody.contains("repetition_penalty"), "repetition_penalty must be absent in: $sentBody")
    }

    @Test
    fun requestCompletion_includesGenerationParamsFromProviderConfig() = runTest {
        val captured = mutableListOf<HttpRequestData>()
        val localProviderConfig = AiProviderConfigModel(
            baseUrl = "http://127.0.0.1:8080/v1/",
            modelId = "default_model",
            systemPrompt = "local system prompt",
            isApiKeyRequired = false,
            maxTokens = TEST_MAX_TOKENS,
            temperature = TEST_TEMPERATURE,
            repetitionPenalty = TEST_REPETITION_PENALTY,
        )
        val dataSource = dataSourceReturning(
            body = successBody("hi"),
            captured = captured,
            providerConfigProvider = AiProviderConfigProvider { localProviderConfig },
        )

        dataSource.requestCompletion(listOf(userMessage("hello")))

        val sentBody = (captured.single().body as TextContent).text
        assertTrue(sentBody.contains("\"max_tokens\":$TEST_MAX_TOKENS"), "max_tokens missing in: $sentBody")
        assertTrue(sentBody.contains("\"temperature\":$TEST_TEMPERATURE"), "temperature missing in: $sentBody")
        assertTrue(
            sentBody.contains("\"repetition_penalty\":$TEST_REPETITION_PENALTY"),
            "repetition_penalty missing in: $sentBody",
        )
    }

    @Test
    fun requestCompletion_onServerError_throwsClientRequestExceptionWithStatus() = runTest {
        val client = HttpClient(
            MockEngine { respondError(HttpStatusCode.Unauthorized) },
        ) {
            expectSuccess = true
            install(ContentNegotiation) { json(lenientJson) }
        }
        val dataSource = DeepSeekRemoteDataSourceImpl(
            httpClient = client,
            promptConfig = testPromptConfig,
            modelProvider = testModelProvider,
            json = lenientJson,
        )

        val exception = assertFailsWith<ClientRequestException> {
            dataSource.requestCompletion(listOf(userMessage("hello")))
        }
        assertEquals(HttpStatusCode.Unauthorized, exception.response.status)
    }

    @Test
    fun requestCompletionStream_enablesStreaming() = runTest {
        val captured = mutableListOf<HttpRequestData>()
        val dataSource = dataSourceReturning(body = "", captured = captured)

        dataSource.requestCompletionStream(listOf(userMessage("hello"))).toList()

        val sentBody = (captured.single().body as TextContent).text
        assertTrue(sentBody.contains("\"stream\":true"), "stream flag missing in: $sentBody")
    }

    @Test
    fun requestCompletionStream_emitsDeltaContentInOrder() = runTest {
        val sseBody = buildString {
            append("data: {\"choices\":[{\"delta\":{\"content\":\"Hel\"}}]}\n\n")
            append("data: {\"choices\":[{\"delta\":{\"content\":\"lo\"}}]}\n\n")
            append("data: [DONE]\n\n")
        }
        val dataSource = dataSourceReturning(body = sseBody)

        val chunks = dataSource.requestCompletionStream(listOf(userMessage("hello"))).toList()

        assertEquals(listOf("Hel", "lo"), chunks.map { chunk -> chunk.text })
    }

    @Test
    fun requestCompletionStream_emitsModelIdFromChunks() = runTest {
        val sseBody = buildString {
            append("data: {\"choices\":[{\"delta\":{\"content\":\"Hel\"}}],\"model\":\"deepseek-chat\"}\n\n")
            append("data: {\"choices\":[{\"delta\":{\"content\":\"lo\"}}],\"model\":\"deepseek-chat\"}\n\n")
            append("data: [DONE]\n\n")
        }
        val dataSource = dataSourceReturning(body = sseBody)

        val chunks = dataSource.requestCompletionStream(listOf(userMessage("hello"))).toList()

        assertEquals(listOf("deepseek-chat", "deepseek-chat"), chunks.map { chunk -> chunk.modelId })
    }

    @Test
    fun requestCompletionStream_onPlainJsonResponse_emitsFullTextAsSingleChunk() = runTest {
        val body = """{"choices":[{"message":{"role":"assistant","content":"Full reply"}}]}"""
        val dataSource = dataSourceReturning(body = body)

        val chunks = dataSource.requestCompletionStream(listOf(userMessage("hello"))).toList()

        assertEquals(listOf("Full reply"), chunks.map { chunk -> chunk.text })
    }

    @Test
    fun requestCompletionStream_onPlainJsonResponse_carriesTriageThrough() = runTest {
        val body = """
            {"choices":[{"message":{"role":"assistant","content":"answer"}}],
             "triage":{"route":"EMERGENCY","status":"OK","confidence":0.98,"explain":"why"}}
        """.trimIndent()
        val dataSource = dataSourceReturning(body = body)

        val chunk = dataSource.requestCompletionStream(listOf(userMessage("hello"))).toList().single()

        assertEquals("EMERGENCY", chunk.triage?.route)
        assertEquals("OK", chunk.triage?.status)
        assertEquals(0.98, chunk.triage?.confidence)
        assertEquals("why", chunk.triage?.explain)
    }

    @Test
    fun requestCompletionStream_onSseFinalChunkWithTriageAndNoDelta_carriesTriageThrough() = runTest {
        val sseBody = buildString {
            append("data: {\"choices\":[{\"delta\":{\"content\":\"Hi\"}}]}\n\n")
            append(
                "data: {\"choices\":[{\"index\":0,\"delta\":{},\"finish_reason\":\"stop\"}]," +
                    "\"triage\":{\"route\":\"EMERGENCY\",\"route_label\":\"Экстренно\",\"status\":\"OK\"," +
                    "\"status_label\":\"Ответ проверен\",\"confidence\":0.996,\"crisis\":true," +
                    "\"spec_version\":\"v2\",\"cost_usd\":0.0001,\"self_check_verdict\":\"AGREE\"}}\n\n",
            )
            append("data: [DONE]\n\n")
        }
        val dataSource = dataSourceReturning(body = sseBody)

        val chunks = dataSource.requestCompletionStream(listOf(userMessage("hello"))).toList()

        assertEquals(listOf("Hi", ""), chunks.map { chunk -> chunk.text })
        val triageChunk = chunks.last()
        assertEquals("EMERGENCY", triageChunk.triage?.route)
        assertEquals("Экстренно", triageChunk.triage?.routeLabel)
        assertEquals(true, triageChunk.triage?.crisis)
    }

    @Test
    fun requestCompletionStream_onSseResponse_leavesTriageNull() = runTest {
        val sseBody = buildString {
            append("data: {\"choices\":[{\"delta\":{\"content\":\"Hel\"}}]}\n\n")
            append("data: [DONE]\n\n")
        }
        val dataSource = dataSourceReturning(body = sseBody)

        val chunks = dataSource.requestCompletionStream(listOf(userMessage("hello"))).toList()

        assertTrue(chunks.all { chunk -> chunk.triage == null })
    }

    @Test
    fun requestCompletionStream_on4xxError_throwsClientRequestException() = runTest {
        val client = HttpClient(
            MockEngine { respondError(HttpStatusCode.Unauthorized) },
        ) {
            expectSuccess = true
            install(ContentNegotiation) { json(lenientJson) }
        }
        val dataSource = DeepSeekRemoteDataSourceImpl(
            httpClient = client,
            promptConfig = testPromptConfig,
            modelProvider = testModelProvider,
            json = lenientJson,
        )

        val exception = assertFailsWith<ClientRequestException> {
            dataSource.requestCompletionStream(listOf(userMessage("hello"))).toList()
        }
        assertEquals(HttpStatusCode.Unauthorized, exception.response.status)
    }

    private val lenientJson: Json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    private val testPromptConfig = DeepSeekPromptConfigModel(
        systemPrompt = "You are a test system prompt.",
    )

    private val testModelProvider = DeepSeekModelProvider { "test-model" }

    private fun dataSourceReturning(
        body: String,
        captured: MutableList<HttpRequestData> = mutableListOf(),
        promptConfig: DeepSeekPromptConfigModel = testPromptConfig,
        modelProvider: DeepSeekModelProvider = testModelProvider,
        providerConfigProvider: AiProviderConfigProvider? = null,
    ): DeepSeekRemoteDataSourceImpl {
        val client = HttpClient(
            MockEngine { request ->
                captured += request
                respond(
                    content = body,
                    status = HttpStatusCode.OK,
                    headers = headersOf(HttpHeaders.ContentType, ContentType.Application.Json.toString()),
                )
            },
        ) {
            install(ContentNegotiation) { json(lenientJson) }
        }
        return if (providerConfigProvider != null) {
            DeepSeekRemoteDataSourceImpl(
                httpClient = client,
                promptConfig = promptConfig,
                modelProvider = modelProvider,
                json = lenientJson,
                providerConfigProvider = providerConfigProvider,
            )
        } else {
            DeepSeekRemoteDataSourceImpl(
                httpClient = client,
                promptConfig = promptConfig,
                modelProvider = modelProvider,
                json = lenientJson,
            )
        }
    }

    private fun successBody(content: String): String =
        """{"choices":[{"message":{"role":"assistant","content":"$content"}}]}"""

    private fun userMessage(content: String): ChatMessageRequestModel =
        ChatMessageRequestModel(role = "user", content = content)
}
