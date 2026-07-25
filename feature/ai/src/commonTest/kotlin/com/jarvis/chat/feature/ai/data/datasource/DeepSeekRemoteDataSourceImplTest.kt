package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
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
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

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
        )

        val exception = assertFailsWith<ClientRequestException> {
            dataSource.requestCompletion(listOf(userMessage("hello")))
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
        return DeepSeekRemoteDataSourceImpl(httpClient = client, promptConfig = promptConfig, modelProvider = modelProvider)
    }

    private fun successBody(content: String): String =
        """{"choices":[{"message":{"role":"assistant","content":"$content"}}]}"""

    private fun userMessage(content: String): ChatMessageRequestModel =
        ChatMessageRequestModel(role = "user", content = content)
}
