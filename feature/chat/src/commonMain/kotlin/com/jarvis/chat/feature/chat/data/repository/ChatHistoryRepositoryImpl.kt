package com.jarvis.chat.feature.chat.data.repository

import com.jarvis.chat.feature.chat.data.datasource.ChatHistoryLocalDataSource
import com.jarvis.chat.feature.chat.data.mapper.toChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.mapper.toHistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class ChatHistoryRepositoryImpl(
    private val localDataSource: ChatHistoryLocalDataSource,
) : ChatHistoryRepository {

    override suspend fun loadMessages(): List<HistoryMessageModel> =
        localDataSource.readHistory().messages.map { message -> message.toHistoryMessageModel() }

    override suspend fun saveMessages(messages: List<HistoryMessageModel>) {
        localDataSource.writeHistory(messages.toChatHistoryDataModel())
    }

    override suspend fun exportMessages(messages: List<HistoryMessageModel>): String =
        localDataSource.writeExport(messages.toChatHistoryDataModel())

    override suspend fun importMessages(
        json: String,
        strategy: ImportStrategy,
        current: List<HistoryMessageModel>,
    ): List<HistoryMessageModel> {
        val imported = localDataSource.parseHistory(json).messages
            .map { message -> message.toHistoryMessageModel() }
        val result = when (strategy) {
            ImportStrategy.REPLACE -> imported
            ImportStrategy.MERGE -> mergeById(current = current, imported = imported)
        }
        saveMessages(result)
        return result
    }

    private fun mergeById(
        current: List<HistoryMessageModel>,
        imported: List<HistoryMessageModel>,
    ): List<HistoryMessageModel> {
        val messagesById = LinkedHashMap<String, HistoryMessageModel>()
        current.forEach { message -> messagesById[message.id] = message }
        imported.forEach { message -> messagesById[message.id] = message }
        return messagesById.values.toList()
    }
}
