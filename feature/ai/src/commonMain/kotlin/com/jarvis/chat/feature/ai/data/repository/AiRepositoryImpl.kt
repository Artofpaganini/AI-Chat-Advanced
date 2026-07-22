package com.jarvis.chat.feature.ai.data.repository

import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSource
import com.jarvis.chat.feature.ai.data.mapper.toChatMessageModel
import com.jarvis.chat.feature.ai.data.mapper.toChatMessageRequestModel
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.repository.AiRepository

internal class AiRepositoryImpl(
    private val remoteDataSource: DeepSeekRemoteDataSource,
) : AiRepository {

    override suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel {
        val requestMessages = history.map { message -> message.toChatMessageRequestModel() }
        val response = remoteDataSource.requestCompletion(requestMessages)
        return response.toChatMessageModel()
    }
}
