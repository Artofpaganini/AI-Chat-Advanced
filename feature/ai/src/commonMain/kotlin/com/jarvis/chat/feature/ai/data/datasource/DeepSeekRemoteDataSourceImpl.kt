package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.ChatCompletionRequestModel
import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

private const val COMPLETIONS_PATH = "chat/completions"
private const val CHAT_MODEL = "deepseek-chat"
private const val ROLE_SYSTEM = "system"
private const val SYSTEM_PROMPT =
    "You are Jarvis, a concise and helpful voice companion. Keep answers clear and easy to read aloud."

internal class DeepSeekRemoteDataSourceImpl(
    private val httpClient: HttpClient,
) : DeepSeekRemoteDataSource {

    override suspend fun requestCompletion(
        messages: List<ChatMessageRequestModel>,
    ): ChatCompletionResponseModel {
        val systemMessage = ChatMessageRequestModel(role = ROLE_SYSTEM, content = SYSTEM_PROMPT)
        val requestBody = ChatCompletionRequestModel(
            model = CHAT_MODEL,
            messages = listOf(systemMessage) + messages,
            stream = false,
        )
        return httpClient.post(COMPLETIONS_PATH) {
            contentType(ContentType.Application.Json)
            setBody(requestBody)
        }.body()
    }
}
