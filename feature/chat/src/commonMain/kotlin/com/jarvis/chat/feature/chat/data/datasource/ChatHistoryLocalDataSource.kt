package com.jarvis.chat.feature.chat.data.datasource

import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.model.ChatSessionsIndexDataModel

internal interface ChatHistoryLocalDataSource {

    suspend fun readSessionsIndex(): ChatSessionsIndexDataModel?

    suspend fun writeSessionsIndex(index: ChatSessionsIndexDataModel)

    suspend fun readLegacyHistory(): ChatHistoryDataModel

    suspend fun readHistory(sessionId: String): ChatHistoryDataModel

    suspend fun writeHistory(sessionId: String, history: ChatHistoryDataModel)

    suspend fun deleteHistory(sessionId: String)

    suspend fun writeExport(history: ChatHistoryDataModel): String

    fun parseHistory(rawJson: String): ChatHistoryDataModel
}
