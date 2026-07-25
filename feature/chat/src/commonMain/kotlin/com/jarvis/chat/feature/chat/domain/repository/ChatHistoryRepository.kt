package com.jarvis.chat.feature.chat.domain.repository

import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy

internal interface ChatHistoryRepository {

    suspend fun loadMessages(): List<HistoryMessageModel>

    suspend fun saveMessages(messages: List<HistoryMessageModel>)

    suspend fun clearMessages()

    suspend fun exportMessages(messages: List<HistoryMessageModel>): String

    suspend fun importMessages(
        json: String,
        strategy: ImportStrategy,
        current: List<HistoryMessageModel>,
    ): List<HistoryMessageModel>
}
