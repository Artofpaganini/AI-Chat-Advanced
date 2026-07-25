package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class DeleteMessageUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(
        messages: List<HistoryMessageModel>,
        messageId: String,
    ): Result<List<HistoryMessageModel>> = runCatching {
        val updatedMessages = messages.filterNot { message -> message.id == messageId }
        repository.saveMessages(updatedMessages)
        updatedMessages
    }
}
