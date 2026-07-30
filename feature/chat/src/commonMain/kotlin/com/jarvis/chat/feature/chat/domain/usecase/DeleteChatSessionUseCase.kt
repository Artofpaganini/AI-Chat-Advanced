package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.model.ChatSessionsModel
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class DeleteChatSessionUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(sessionId: String): Result<ChatSessionsModel> =
        runCatching { repository.deleteSession(sessionId) }
}
