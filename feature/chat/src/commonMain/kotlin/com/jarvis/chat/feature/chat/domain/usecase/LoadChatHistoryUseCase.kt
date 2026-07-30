package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class LoadChatHistoryUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(sessionId: String): List<HistoryMessageModel> = repository.loadMessages(sessionId)
}
