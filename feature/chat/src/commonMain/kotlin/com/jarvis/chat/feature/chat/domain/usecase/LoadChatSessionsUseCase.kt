package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.model.ChatSessionsModel
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class LoadChatSessionsUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(): ChatSessionsModel = repository.loadSessions()
}
