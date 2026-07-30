package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class SaveChatHistoryUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(sessionId: String, messages: List<HistoryMessageModel>): Result<Unit> =
        runCatching { repository.saveMessages(sessionId, messages) }
}
