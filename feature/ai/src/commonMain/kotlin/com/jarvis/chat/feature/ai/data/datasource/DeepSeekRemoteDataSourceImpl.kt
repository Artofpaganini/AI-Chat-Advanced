package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.ChatCompletionRequestModel
import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import com.jarvis.chat.feature.ai.data.model.ChatStreamChunkDataModel
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigModel
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigProvider
import com.jarvis.chat.feature.ai.domain.model.DeepSeekConfigModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekModelProvider
import com.jarvis.chat.feature.ai.domain.model.DeepSeekPromptConfigModel
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.timeout
import io.ktor.client.request.HttpRequestBuilder
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.preparePost
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsChannel
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emitAll
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json

private const val COMPLETIONS_PATH = "chat/completions"
private const val ROLE_SYSTEM = "system"
private const val STREAM_SOCKET_TIMEOUT_INFINITE_MILLIS = Long.MAX_VALUE

private val NO_OP_PROVIDER_CONFIG = AiProviderConfigModel(
    baseUrl = "",
    modelId = "",
    systemPrompt = "",
    isApiKeyRequired = false,
    adapterPath = null,
)

internal class DeepSeekRemoteDataSourceImpl(
    private val httpClient: HttpClient,
    private val promptConfig: DeepSeekPromptConfigModel,
    private val modelProvider: DeepSeekModelProvider,
    private val json: Json,
    private val providerConfigProvider: AiProviderConfigProvider = AiProviderConfigProvider { NO_OP_PROVIDER_CONFIG },
    private val deepSeekConfig: DeepSeekConfigModel = DeepSeekConfigModel(apiKey = ""),
) : DeepSeekRemoteDataSource {

    override suspend fun requestCompletion(
        messages: List<ChatMessageRequestModel>,
    ): ChatCompletionResponseModel {
        val providerConfig = providerConfigProvider.currentConfig()
        val requestBody = buildRequestBody(messages = messages, stream = false, providerConfig = providerConfig)
        return httpClient.post(providerConfig.baseUrl + COMPLETIONS_PATH) {
            applyAuthHeader(providerConfig = providerConfig)
            contentType(ContentType.Application.Json)
            setBody(requestBody)
        }.body()
    }

    override fun requestCompletionStream(
        messages: List<ChatMessageRequestModel>,
    ): Flow<ChatStreamChunkDataModel> = flow {
        val providerConfig = providerConfigProvider.currentConfig()
        val requestBody = buildRequestBody(messages = messages, stream = true, providerConfig = providerConfig)
        httpClient.preparePost(providerConfig.baseUrl + COMPLETIONS_PATH) {
            applyAuthHeader(providerConfig = providerConfig)
            contentType(ContentType.Application.Json)
            setBody(requestBody)
            timeout { socketTimeoutMillis = STREAM_SOCKET_TIMEOUT_INFINITE_MILLIS }
        }.execute { response ->
            emitAll(sseChunkFlow(channel = response.bodyAsChannel(), json = json))
        }
    }

    private fun HttpRequestBuilder.applyAuthHeader(providerConfig: AiProviderConfigModel) {
        if (providerConfig.isApiKeyRequired) {
            header(HttpHeaders.Authorization, "Bearer ${deepSeekConfig.apiKey}")
        }
    }

    private fun buildRequestBody(
        messages: List<ChatMessageRequestModel>,
        stream: Boolean,
        providerConfig: AiProviderConfigModel,
    ): ChatCompletionRequestModel {
        val systemPrompt = providerConfig.systemPrompt.ifBlank { promptConfig.systemPrompt }
        val systemMessage = ChatMessageRequestModel(role = ROLE_SYSTEM, content = systemPrompt)
        return ChatCompletionRequestModel(
            model = modelProvider.currentModel(),
            messages = listOf(systemMessage) + messages,
            stream = stream,
            adapters = providerConfig.adapterPath,
            maxTokens = providerConfig.maxTokens,
            temperature = providerConfig.temperature,
            repetitionPenalty = providerConfig.repetitionPenalty,
        )
    }
}
