package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class ClearChatHistoryUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(): Result<Unit> =
        runCatching { repository.clearMessages() }
}
