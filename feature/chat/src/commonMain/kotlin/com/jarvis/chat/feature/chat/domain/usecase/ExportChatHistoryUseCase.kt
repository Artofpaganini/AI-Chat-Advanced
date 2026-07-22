package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class ExportChatHistoryUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(messages: List<HistoryMessageModel>): Result<String> =
        runCatching { repository.exportMessages(messages) }
}
