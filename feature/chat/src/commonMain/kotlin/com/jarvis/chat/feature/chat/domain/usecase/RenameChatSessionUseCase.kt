package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class RenameChatSessionUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(sessionId: String, title: String): Result<Unit> =
        runCatching { repository.renameSession(sessionId, title) }
}
