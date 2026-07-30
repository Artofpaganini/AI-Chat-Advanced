package com.jarvis.chat.feature.chat.data.datasource

import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.model.ChatSessionsIndexDataModel
import com.jarvis.chat.feature.chat.domain.model.ChatStorageConfigModel
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import kotlinx.io.buffered
import kotlinx.io.files.Path
import kotlinx.io.files.SystemFileSystem
import kotlinx.io.readString
import kotlinx.io.writeString
import kotlinx.serialization.json.Json

private const val LEGACY_HISTORY_FILE_NAME = "chat_history.json"
private const val EXPORT_FILE_NAME = "chat_history_export.json"
private const val SESSIONS_INDEX_FILE_NAME = "chat_sessions.json"
private const val SESSION_HISTORY_FILE_PREFIX = "chat_history_"
private const val SESSION_HISTORY_FILE_SUFFIX = ".json"
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
    private val legacyHistoryPath: Path = Path(storageConfig.directoryPath, LEGACY_HISTORY_FILE_NAME)
    private val exportPath: Path = Path(storageConfig.directoryPath, EXPORT_FILE_NAME)
    private val sessionsIndexPath: Path = Path(storageConfig.directoryPath, SESSIONS_INDEX_FILE_NAME)

    override suspend fun readSessionsIndex(): ChatSessionsIndexDataModel? = withContext(ioDispatcher) {
        if (!SystemFileSystem.exists(sessionsIndexPath)) {
            return@withContext null
        }
        val content = SystemFileSystem.source(sessionsIndexPath).buffered().use { source -> source.readString() }
        if (content.isBlank()) {
            return@withContext null
        }
        runCatching { json.decodeFromString<ChatSessionsIndexDataModel>(content) }.getOrNull()
    }

    override suspend fun writeSessionsIndex(index: ChatSessionsIndexDataModel) = withContext(ioDispatcher) {
        ensureDirectory()
        val content = json.encodeToString(index)
        SystemFileSystem.sink(sessionsIndexPath).buffered().use { sink -> sink.writeString(content) }
    }

    override suspend fun readLegacyHistory(): ChatHistoryDataModel = readHistoryFrom(legacyHistoryPath)

    override suspend fun readHistory(sessionId: String): ChatHistoryDataModel = readHistoryFrom(sessionHistoryPath(sessionId))

    override suspend fun writeHistory(sessionId: String, history: ChatHistoryDataModel) = withContext(ioDispatcher) {
        ensureDirectory()
        val content = json.encodeToString(history)
        SystemFileSystem.sink(sessionHistoryPath(sessionId)).buffered().use { sink -> sink.writeString(content) }
    }

    override suspend fun deleteHistory(sessionId: String) = withContext(ioDispatcher) {
        val path = sessionHistoryPath(sessionId)
        if (SystemFileSystem.exists(path)) {
            SystemFileSystem.delete(path, mustExist = false)
        }
    }

    override suspend fun writeExport(history: ChatHistoryDataModel): String = withContext(ioDispatcher) {
        ensureDirectory()
        val content = json.encodeToString(history)
        SystemFileSystem.sink(exportPath).buffered().use { sink -> sink.writeString(content) }
        exportPath.toString()
    }

    override fun parseHistory(rawJson: String): ChatHistoryDataModel =
        json.decodeFromString<ChatHistoryDataModel>(rawJson)

    private suspend fun readHistoryFrom(path: Path): ChatHistoryDataModel = withContext(ioDispatcher) {
        if (!SystemFileSystem.exists(path)) {
            return@withContext emptyHistory()
        }
        val content = SystemFileSystem.source(path).buffered().use { source -> source.readString() }
        if (content.isBlank()) {
            return@withContext emptyHistory()
        }
        runCatching { json.decodeFromString<ChatHistoryDataModel>(content) }.getOrElse { emptyHistory() }
    }

    private fun sessionHistoryPath(sessionId: String): Path =
        Path(directoryPath, "$SESSION_HISTORY_FILE_PREFIX$sessionId$SESSION_HISTORY_FILE_SUFFIX")

    private fun ensureDirectory() {
        if (!SystemFileSystem.exists(directoryPath)) {
            SystemFileSystem.createDirectories(directoryPath)
        }
    }

    private fun emptyHistory(): ChatHistoryDataModel =
        ChatHistoryDataModel(version = HISTORY_VERSION, messages = emptyList())
}
