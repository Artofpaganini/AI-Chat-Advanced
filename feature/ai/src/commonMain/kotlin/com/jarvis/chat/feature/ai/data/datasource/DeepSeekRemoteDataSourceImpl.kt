package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.ChatCompletionRequestModel
import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekPromptConfigModel
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

private const val COMPLETIONS_PATH = "chat/completions"
private const val ROLE_SYSTEM = "system"

internal class DeepSeekRemoteDataSourceImpl(
    private val httpClient: HttpClient,
    private val promptConfig: DeepSeekPromptConfigModel,
) : DeepSeekRemoteDataSource {

    override suspend fun requestCompletion(
        messages: List<ChatMessageRequestModel>,
    ): ChatCompletionResponseModel {
        val systemMessage = ChatMessageRequestModel(role = ROLE_SYSTEM, content = promptConfig.systemPrompt)
        val requestBody = ChatCompletionRequestModel(
            model = promptConfig.model,
            messages = listOf(systemMessage) + messages,
            stream = false,
        )
        return httpClient.post(COMPLETIONS_PATH) {
            contentType(ContentType.Application.Json)
            setBody(requestBody)
        }.body()
    }
}
