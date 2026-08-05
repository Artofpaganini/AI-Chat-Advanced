package com.jarvis.chat.feature.ai.data.repository

import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSource
import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSourceImpl
import com.jarvis.chat.feature.ai.data.model.ChatChoiceResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatStreamChunkDataModel
import com.jarvis.chat.feature.ai.data.model.GatewaySignalResponseModel
import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.AiException
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigModel
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigProvider
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekModelProvider
import com.jarvis.chat.feature.ai.domain.model.DeepSeekPromptConfigModel
import com.jarvis.chat.feature.ai.domain.model.GatewayVerdictModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.client.plugins.HttpRequestTimeoutException
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logger
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.request.HttpRequestBuilder
import io.ktor.http.ContentType
import io.ktor.http.Headers
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.http.headersOf
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import kotlinx.io.IOException
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

private const val TEST_TIMEOUT_MILLIS = 60_000L

class AiRepositoryImplTest {

    private val testProviderConfigProvider = AiProviderConfigProvider {
        AiProviderConfigModel(
            baseUrl = "https://deepseek.test/",
            modelId = "test-model",
            systemPrompt = "test system prompt",
            isApiKeyRequired = true,
        )
    }

    @Test
    fun sendMessage_forwardsHistoryAsRequestMessagesInSameOrder() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(reply = "ok")
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        repository.sendMessage(
            listOf(
                ChatMessageModel(author = MessageAuthor.USER, text = "first"),
                ChatMessageModel(author = MessageAuthor.ASSISTANT, text = "second"),
                ChatMessageModel(author = MessageAuthor.USER, text = "third"),
            ),
        )

        assertEquals(
            listOf("user" to "first", "assistant" to "second", "user" to "third"),
            dataSource.received.map { message -> message.role to message.content },
        )
    }

    @Test
    fun sendMessage_mapsResponseToAssistantMessage() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(reply = "  answer  ")
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        val result = repository.sendMessage(
            listOf(ChatMessageModel(author = MessageAuthor.USER, text = "question")),
        )

        assertEquals(MessageAuthor.ASSISTANT, result.author)
        assertEquals("answer", result.text)
    }

    @Test
    fun sendMessage_withEmptyHistory_stillCallsDataSource() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(reply = "hi")
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        val result = repository.sendMessage(emptyList())

        assertTrue(dataSource.received.isEmpty())
        assertEquals("hi", result.text)
    }

    @Test
    fun sendMessage_whenDataSourceFails_throwsAiExceptionWithMappedError() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(error = IllegalStateException("network down"))
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        val error = assertFailsWith<AiException> {
            repository.sendMessage(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "x")))
        }

        assertEquals(AiErrorModel.Unknown, error.error)
    }

    @Test
    fun sendMessage_whenDataSourceFailsWithIoException_throwsAiExceptionWithNoConnection() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(error = IOException("network down"))
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        val error = assertFailsWith<AiException> {
            repository.sendMessage(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "x")))
        }

        assertEquals(AiErrorModel.NoConnection, error.error)
    }

    @Test
    fun sendMessage_whenDataSourceFailsWithTimeout_throwsAiExceptionWithTimeout() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(error = HttpRequestTimeoutException(HttpRequestBuilder()))
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        val error = assertFailsWith<AiException> {
            repository.sendMessage(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "x")))
        }

        assertEquals(AiErrorModel.Timeout, error.error)
    }

    @Test
    fun sendMessage_whenResponseHasNoChoices_returnsEmptyText() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(reply = null)
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        val result = repository.sendMessage(
            listOf(ChatMessageModel(author = MessageAuthor.USER, text = "x")),
        )

        assertEquals("", result.text)
    }

    @Test
    fun sendMessageStream_forwardsHistoryAsRequestMessagesInSameOrder() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(chunks = listOf(ChatStreamChunkDataModel(text = "ok")))
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        repository.sendMessageStream(
            listOf(
                ChatMessageModel(author = MessageAuthor.USER, text = "first"),
                ChatMessageModel(author = MessageAuthor.ASSISTANT, text = "second"),
            ),
        ).toList()

        assertEquals(
            listOf("user" to "first", "assistant" to "second"),
            dataSource.received.map { message -> message.role to message.content },
        )
    }

    @Test
    fun sendMessageStream_emitsChunksFromDataSourceInOrder() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(
            chunks = listOf(ChatStreamChunkDataModel(text = "Hel"), ChatStreamChunkDataModel(text = "lo")),
        )
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        val chunks = repository.sendMessageStream(
            listOf(ChatMessageModel(author = MessageAuthor.USER, text = "question")),
        ).toList()

        assertEquals(listOf("Hel", "lo"), chunks.map { chunk -> chunk.text })
    }

    @Test
    fun sendMessageStream_forwardsModelIdFromDataSource() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(
            chunks = listOf(
                ChatStreamChunkDataModel(text = "Hel", modelId = "deepseek-chat"),
                ChatStreamChunkDataModel(text = "lo"),
            ),
        )
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        val chunks = repository.sendMessageStream(
            listOf(ChatMessageModel(author = MessageAuthor.USER, text = "question")),
        ).toList()

        assertEquals(listOf("deepseek-chat", null), chunks.map { chunk -> chunk.modelId })
    }

    @Test
    fun sendMessageStream_onMaskedGatewaySignalFromDataSource_mapsVerdictAndReasonsToDomain() = runTest {
        val gatewaySignal = GatewaySignalResponseModel(
            verdict = "masked",
            reasons = listOf("card", "email", "secret_in_history"),
            maskedCount = 2,
            tokensIn = 1375,
            tokensOut = 462,
            costUsd = 0.000322,
            rateLimitLimit = null,
            rateLimitRemaining = null,
            requestId = "req-1",
        )
        val dataSource = FakeDeepSeekRemoteDataSource(
            chunks = listOf(ChatStreamChunkDataModel(text = "Hi", gatewaySignal = gatewaySignal)),
        )
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        val chunk = repository.sendMessageStream(
            listOf(ChatMessageModel(author = MessageAuthor.USER, text = "question")),
        ).toList().last()

        assertEquals(GatewayVerdictModel.MASKED, chunk.gatewaySignal?.verdict)
        assertEquals(listOf("card", "email", "secret_in_history"), chunk.gatewaySignal?.reasons)
        assertEquals(2, chunk.gatewaySignal?.maskedCount)
        assertEquals(1375, chunk.gatewaySignal?.tokensIn)
        assertEquals(462, chunk.gatewaySignal?.tokensOut)
        assertEquals(0.000322, chunk.gatewaySignal?.costUsd)
    }

    @Test
    fun sendMessageStream_throughRealDataSourceWithMaskedGatewayHeaders_carriesVerdictToRepositoryOutput() = runTest {
        val sseBody = buildString {
            append("data: {\"choices\":[{\"delta\":{\"content\":\"Hi\"}}]}\n\n")
            append("data: [DONE]\n\n")
        }
        val gatewayHeaders = headersOf(
            "X-Gateway-Verdict" to listOf("masked"),
            "X-Gateway-Reasons" to listOf("card,email,secret_in_history"),
            "X-Gateway-Masked-Count" to listOf("2"),
            "X-Gateway-Tokens-In" to listOf("1375"),
            "X-Gateway-Tokens-Out" to listOf("462"),
            "X-Gateway-Cost-Usd" to listOf("0.000322"),
        )
        val lenientJson = Json { ignoreUnknownKeys = true; isLenient = true }
        val client = HttpClient(
            MockEngine {
                respond(
                    content = sseBody,
                    status = HttpStatusCode.OK,
                    headers = Headers.build {
                        append(HttpHeaders.ContentType, ContentType.Application.Json.toString())
                        appendAll(gatewayHeaders)
                    },
                )
            },
        ) {
            install(ContentNegotiation) { json(lenientJson) }
        }
        val realDataSource = DeepSeekRemoteDataSourceImpl(
            httpClient = client,
            promptConfig = DeepSeekPromptConfigModel(systemPrompt = "test system prompt"),
            modelProvider = DeepSeekModelProvider { "test-model" },
            json = lenientJson,
        )
        val repository = AiRepositoryImpl(remoteDataSource = realDataSource, providerConfigProvider = testProviderConfigProvider)

        val chunk = repository.sendMessageStream(
            listOf(ChatMessageModel(author = MessageAuthor.USER, text = "question")),
        ).toList().last()

        assertEquals(GatewayVerdictModel.MASKED, chunk.gatewaySignal?.verdict)
        assertEquals(listOf("card", "email", "secret_in_history"), chunk.gatewaySignal?.reasons)
    }

    @Test
    fun sendMessageStream_withProductionHttpClientConfig_stillCarriesMaskedVerdictThrough() = runTest {
        val sseBody = buildString {
            append("data: {\"choices\":[{\"delta\":{\"content\":\"Hi\"}}]}\n\n")
            append("data: [DONE]\n\n")
        }
        val gatewayHeaders = headersOf(
            "X-Gateway-Verdict" to listOf("masked"),
            "X-Gateway-Reasons" to listOf("card,email,secret_in_history"),
        )
        val lenientJson = Json { ignoreUnknownKeys = true; isLenient = true }
        val client = HttpClient(
            MockEngine {
                respond(
                    content = sseBody,
                    status = HttpStatusCode.OK,
                    headers = Headers.build {
                        append(HttpHeaders.ContentType, ContentType.Application.Json.toString())
                        appendAll(gatewayHeaders)
                    },
                )
            },
        ) {
            expectSuccess = true
            install(ContentNegotiation) { json(lenientJson) }
            install(HttpTimeout) {
                requestTimeoutMillis = TEST_TIMEOUT_MILLIS
                connectTimeoutMillis = TEST_TIMEOUT_MILLIS
                socketTimeoutMillis = TEST_TIMEOUT_MILLIS
            }
            install(Logging) {
                logger = object : Logger {
                    override fun log(message: String) = Unit
                }
                level = LogLevel.HEADERS
                sanitizeHeader { header -> header == HttpHeaders.Authorization }
            }
            defaultRequest { contentType(ContentType.Application.Json) }
        }
        val realDataSource = DeepSeekRemoteDataSourceImpl(
            httpClient = client,
            promptConfig = DeepSeekPromptConfigModel(systemPrompt = "test system prompt"),
            modelProvider = DeepSeekModelProvider { "test-model" },
            json = lenientJson,
        )
        val repository = AiRepositoryImpl(remoteDataSource = realDataSource, providerConfigProvider = testProviderConfigProvider)

        val chunk = repository.sendMessageStream(
            listOf(ChatMessageModel(author = MessageAuthor.USER, text = "question")),
        ).toList().last()

        assertEquals(GatewayVerdictModel.MASKED, chunk.gatewaySignal?.verdict)
    }

    @Test
    fun sendMessageStream_whenDataSourceFails_throwsAiExceptionWithMappedError() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(error = IllegalStateException("network down"))
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        val error = assertFailsWith<AiException> {
            repository.sendMessageStream(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "x"))).toList()
        }

        assertEquals(AiErrorModel.Unknown, error.error)
    }

    @Test
    fun sendMessageStream_onCancellation_rethrowsCancellationInsteadOfWrapping() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(error = CancellationException("cancelled"))
        val repository = AiRepositoryImpl(remoteDataSource = dataSource, providerConfigProvider = testProviderConfigProvider)

        assertFailsWith<CancellationException> {
            repository.sendMessageStream(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "x"))).toList()
        }
    }

    private class FakeDeepSeekRemoteDataSource(
        private val reply: String? = null,
        private val chunks: List<ChatStreamChunkDataModel> = emptyList(),
        private val error: Throwable? = null,
    ) : DeepSeekRemoteDataSource {

        val received: MutableList<ChatMessageRequestModel> = mutableListOf()

        override suspend fun requestCompletion(
            messages: List<ChatMessageRequestModel>,
        ): ChatCompletionResponseModel {
            received += messages
            error?.let { failure -> throw failure }
            val choices = reply?.let { content ->
                listOf(
                    ChatChoiceResponseModel(
                        message = ChatMessageResponseModel(role = "assistant", content = content),
                    ),
                )
            }.orEmpty()
            return ChatCompletionResponseModel(choices = choices)
        }

        override fun requestCompletionStream(
            messages: List<ChatMessageRequestModel>,
        ): Flow<ChatStreamChunkDataModel> = flow {
            received += messages
            error?.let { failure -> throw failure }
            chunks.forEach { chunk -> emit(chunk) }
        }

        override suspend fun requestRawCompletion(
            messages: List<ChatMessageRequestModel>,
            maxTokens: Int,
        ): ChatCompletionResponseModel = requestCompletion(messages)
    }
}
