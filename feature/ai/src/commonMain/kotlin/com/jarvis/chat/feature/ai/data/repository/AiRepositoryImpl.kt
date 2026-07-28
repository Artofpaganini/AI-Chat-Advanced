package com.jarvis.chat.feature.ai.data.repository

import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSource
import com.jarvis.chat.feature.ai.data.mapper.toAiErrorModel
import com.jarvis.chat.feature.ai.data.mapper.toChatMessageModel
import com.jarvis.chat.feature.ai.data.mapper.toChatMessageRequestModel
import com.jarvis.chat.feature.ai.data.mapper.toChatStreamChunkModel
import com.jarvis.chat.feature.ai.domain.model.AiException
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.ChatStreamChunkModel
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map

internal class AiRepositoryImpl(
    private val remoteDataSource: DeepSeekRemoteDataSource,
) : AiRepository {

    @Suppress("TooGenericExceptionCaught", "SwallowedException")
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

    override fun sendMessageStream(history: List<ChatMessageModel>): Flow<ChatStreamChunkModel> {
        val requestMessages = history.map { message -> message.toChatMessageRequestModel() }
        return remoteDataSource.requestCompletionStream(requestMessages)
            .map { chunk -> chunk.toChatStreamChunkModel() }
            .catch { throwable ->
                if (throwable is CancellationException) {
                    throw throwable
                }
                throw AiException(error = throwable.toAiErrorModel())
            }
    }
}
