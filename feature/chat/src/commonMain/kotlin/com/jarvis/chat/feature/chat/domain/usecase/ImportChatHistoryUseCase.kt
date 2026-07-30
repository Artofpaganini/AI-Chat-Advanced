package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class ImportChatHistoryUseCase(
    private val repository: ChatHistoryRepository,
) {

    suspend operator fun invoke(
        sessionId: String,
        json: String,
        strategy: ImportStrategy,
        current: List<HistoryMessageModel>,
    ): Result<List<HistoryMessageModel>> =
        runCatching { repository.importMessages(sessionId = sessionId, json = json, strategy = strategy, current = current) }
}
