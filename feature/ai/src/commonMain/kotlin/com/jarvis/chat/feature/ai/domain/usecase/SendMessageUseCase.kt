package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import kotlinx.coroutines.CancellationException

class SendMessageUseCase(
    private val repository: AiRepository,
) {

    @Suppress("TooGenericExceptionCaught")
    suspend operator fun invoke(history: List<ChatMessageModel>): Result<ChatMessageModel> =
        try {
            Result.success(repository.sendMessage(history))
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (throwable: Throwable) {
            Result.failure(throwable)
        }
}
