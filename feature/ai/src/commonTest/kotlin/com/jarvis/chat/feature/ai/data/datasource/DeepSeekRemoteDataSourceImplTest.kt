package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekPromptConfigModel
import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.client.engine.mock.respondError
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
import kotlin.test.assertFails
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
    fun requestCompletion_sendsChatModel() = runTest {
        val captured = mutableListOf<HttpRequestData>()
        val dataSource = dataSourceReturning(body = successBody("hi"), captured = captured)

        dataSource.requestCompletion(listOf(userMessage("hello")))

        val sentBody = (captured.single().body as TextContent).text
        assertTrue(sentBody.contains("\"model\":\"${testPromptConfig.model}\""), "model missing in: $sentBody")
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
    fun requestCompletion_onServerError_throws() = runTest {
        val client = HttpClient(
            MockEngine { respondError(HttpStatusCode.Unauthorized) },
        ) {
            install(ContentNegotiation) { json(lenientJson) }
        }
        val dataSource = DeepSeekRemoteDataSourceImpl(httpClient = client, promptConfig = testPromptConfig)

        assertFails { dataSource.requestCompletion(listOf(userMessage("hello"))) }
    }

    private val lenientJson: Json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    private val testPromptConfig = DeepSeekPromptConfigModel(
        model = "test-model",
        systemPrompt = "You are a test system prompt.",
    )

    private fun dataSourceReturning(
        body: String,
        captured: MutableList<HttpRequestData> = mutableListOf(),
        promptConfig: DeepSeekPromptConfigModel = testPromptConfig,
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
        return DeepSeekRemoteDataSourceImpl(httpClient = client, promptConfig = promptConfig)
    }

    private fun successBody(content: String): String =
        """{"choices":[{"message":{"role":"assistant","content":"$content"}}]}"""

    private fun userMessage(content: String): ChatMessageRequestModel =
        ChatMessageRequestModel(role = "user", content = content)
}
