package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.ChatCompletionRequestModel
import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekModelProvider
import com.jarvis.chat.feature.ai.domain.model.DeepSeekPromptConfigModel
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.timeout
import io.ktor.client.request.post
import io.ktor.client.request.preparePost
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsChannel
import io.ktor.http.ContentType
import io.ktor.http.contentType
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emitAll
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json

private const val COMPLETIONS_PATH = "chat/completions"
private const val ROLE_SYSTEM = "system"
private const val STREAM_SOCKET_TIMEOUT_INFINITE_MILLIS = Long.MAX_VALUE

internal class DeepSeekRemoteDataSourceImpl(
    private val httpClient: HttpClient,
    private val promptConfig: DeepSeekPromptConfigModel,
    private val modelProvider: DeepSeekModelProvider,
    private val json: Json,
) : DeepSeekRemoteDataSource {

    override suspend fun requestCompletion(
        messages: List<ChatMessageRequestModel>,
    ): ChatCompletionResponseModel {
        val requestBody = buildRequestBody(messages = messages, stream = false)
        return httpClient.post(COMPLETIONS_PATH) {
            contentType(ContentType.Application.Json)
            setBody(requestBody)
        }.body()
    }

    override fun requestCompletionStream(
        messages: List<ChatMessageRequestModel>,
    ): Flow<String> = flow {
        val requestBody = buildRequestBody(messages = messages, stream = true)
        httpClient.preparePost(COMPLETIONS_PATH) {
            contentType(ContentType.Application.Json)
            setBody(requestBody)
            timeout { socketTimeoutMillis = STREAM_SOCKET_TIMEOUT_INFINITE_MILLIS }
        }.execute { response ->
            emitAll(sseChunkTextFlow(channel = response.bodyAsChannel(), json = json))
        }
    }

    private fun buildRequestBody(
        messages: List<ChatMessageRequestModel>,
        stream: Boolean,
    ): ChatCompletionRequestModel {
        val systemMessage = ChatMessageRequestModel(role = ROLE_SYSTEM, content = promptConfig.systemPrompt)
        return ChatCompletionRequestModel(
            model = modelProvider.currentModel(),
            messages = listOf(systemMessage) + messages,
            stream = stream,
        )
    }
}
