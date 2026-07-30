package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class SwitchChatSessionUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(sessionId: String): Result<Unit> = runCatching { repository.switchSession(sessionId) }
}
