package com.jarvis.chat.feature.chat.data.datasource

import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel

internal interface ChatHistoryLocalDataSource {

    suspend fun readHistory(): ChatHistoryDataModel

    suspend fun writeHistory(history: ChatHistoryDataModel)

    suspend fun writeExport(history: ChatHistoryDataModel): String

    fun parseHistory(rawJson: String): ChatHistoryDataModel
}
