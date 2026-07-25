package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import kotlinx.coroutines.flow.Flow

class SendMessageStreamUseCase(
    private val repository: AiRepository,
) {

    operator fun invoke(history: List<ChatMessageModel>): Flow<String> = repository.sendMessageStream(history)
}
