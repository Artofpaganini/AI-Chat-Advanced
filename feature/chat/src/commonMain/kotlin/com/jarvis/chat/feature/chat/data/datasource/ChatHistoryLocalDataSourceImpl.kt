package com.jarvis.chat.feature.chat.data.datasource

import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel
import com.jarvis.chat.feature.chat.domain.model.ChatStorageConfigModel
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import kotlinx.io.buffered
import kotlinx.io.files.Path
import kotlinx.io.files.SystemFileSystem
import kotlinx.io.readString
import kotlinx.io.writeString
import kotlinx.serialization.json.Json

private const val HISTORY_FILE_NAME = "chat_history.json"
private const val EXPORT_FILE_NAME = "chat_history_export.json"
private const val HISTORY_VERSION = 1

internal class ChatHistoryLocalDataSourceImpl(
    storageConfig: ChatStorageConfigModel,
    private val ioDispatcher: CoroutineDispatcher,
) : ChatHistoryLocalDataSource {

    private val json: Json = Json {
        ignoreUnknownKeys = true
        prettyPrint = true
    }

    private val directoryPath: Path = Path(storageConfig.directoryPath)
    private val historyPath: Path = Path(storageConfig.directoryPath, HISTORY_FILE_NAME)
    private val exportPath: Path = Path(storageConfig.directoryPath, EXPORT_FILE_NAME)

    override suspend fun readHistory(): ChatHistoryDataModel = withContext(ioDispatcher) {
        if (!SystemFileSystem.exists(historyPath)) {
            return@withContext emptyHistory()
        }
        val content = SystemFileSystem.source(historyPath).buffered().use { source -> source.readString() }
        if (content.isBlank()) {
            return@withContext emptyHistory()
        }
        runCatching { json.decodeFromString<ChatHistoryDataModel>(content) }.getOrElse { emptyHistory() }
    }

    override suspend fun writeHistory(history: ChatHistoryDataModel) = withContext(ioDispatcher) {
        ensureDirectory()
        val content = json.encodeToString(history)
        SystemFileSystem.sink(historyPath).buffered().use { sink -> sink.writeString(content) }
    }

    override suspend fun writeExport(history: ChatHistoryDataModel): String = withContext(ioDispatcher) {
        ensureDirectory()
        val content = json.encodeToString(history)
        SystemFileSystem.sink(exportPath).buffered().use { sink -> sink.writeString(content) }
        exportPath.toString()
    }

    override fun parseHistory(rawJson: String): ChatHistoryDataModel =
        json.decodeFromString<ChatHistoryDataModel>(rawJson)

    private fun ensureDirectory() {
        if (!SystemFileSystem.exists(directoryPath)) {
            SystemFileSystem.createDirectories(directoryPath)
        }
    }

    private fun emptyHistory(): ChatHistoryDataModel =
        ChatHistoryDataModel(version = HISTORY_VERSION, messages = emptyList())
}
