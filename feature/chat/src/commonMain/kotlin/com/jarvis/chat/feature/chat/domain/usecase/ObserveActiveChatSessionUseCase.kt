package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository
import kotlinx.coroutines.flow.StateFlow

internal class ObserveActiveChatSessionUseCase(
    private val repository: ChatHistoryRepository,
) {

    operator fun invoke(): StateFlow<String?> = repository.observeActiveSessionId()
}
