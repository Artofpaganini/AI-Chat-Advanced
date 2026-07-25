package com.jarvis.chat.feature.ai.data.repository

import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSource
import com.jarvis.chat.feature.ai.data.mapper.toAiErrorModel
import com.jarvis.chat.feature.ai.data.mapper.toChatMessageModel
import com.jarvis.chat.feature.ai.data.mapper.toChatMessageRequestModel
import com.jarvis.chat.feature.ai.domain.model.AiException
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import kotlinx.coroutines.CancellationException

internal class AiRepositoryImpl(
    private val remoteDataSource: DeepSeekRemoteDataSource,
) : AiRepository {

    override suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel {
        val requestMessages = history.map { message -> message.toChatMessageRequestModel() }
        val response = try {
            remoteDataSource.requestCompletion(requestMessages)
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (throwable: Throwable) {
            throw AiException(error = throwable.toAiErrorModel())
        }
        return response.toChatMessageModel()
    }
}
