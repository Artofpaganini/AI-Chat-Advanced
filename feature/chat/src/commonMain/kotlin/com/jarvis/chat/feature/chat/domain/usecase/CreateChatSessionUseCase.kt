package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class CreateChatSessionUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(): Result<ChatSessionModel> = runCatching { repository.createSession() }
}
