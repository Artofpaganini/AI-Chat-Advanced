package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.repository.AiRepository

class SendMessageUseCase internal constructor(
    private val repository: AiRepository,
) {

    suspend operator fun invoke(history: List<ChatMessageModel>): Result<ChatMessageModel> =
        runCatching { repository.sendMessage(history) }
}
