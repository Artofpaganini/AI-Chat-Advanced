package com.jarvis.chat.feature.chat.data.datasource

import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.model.ChatSessionsIndexDataModel
import kotlinx.browser.localStorage
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import org.w3c.dom.get
import org.w3c.dom.set

private const val LEGACY_HISTORY_STORAGE_KEY = "jarvis_chat_history"
private const val EXPORT_STORAGE_KEY = "jarvis_chat_history_export"
private const val SESSIONS_INDEX_STORAGE_KEY = "jarvis_chat_sessions"
private const val SESSION_HISTORY_STORAGE_KEY_PREFIX = "jarvis_chat_history_"
private const val HISTORY_VERSION = 1

internal class WebChatHistoryLocalDataSource(
    private val ioDispatcher: CoroutineDispatcher,
) : ChatHistoryLocalDataSource {

    private val json: Json = Json {
        ignoreUnknownKeys = true
        prettyPrint = true
    }

    override suspend fun readSessionsIndex(): ChatSessionsIndexDataModel? = withContext(ioDispatcher) {
        val content = localStorage[SESSIONS_INDEX_STORAGE_KEY]
        if (content.isNullOrBlank()) {
            return@withContext null
        }
        runCatching { json.decodeFromString<ChatSessionsIndexDataModel>(content) }.getOrNull()
    }

    override suspend fun writeSessionsIndex(index: ChatSessionsIndexDataModel) = withContext(ioDispatcher) {
        localStorage[SESSIONS_INDEX_STORAGE_KEY] = json.encodeToString(index)
    }

    override suspend fun readLegacyHistory(): ChatHistoryDataModel = readHistoryFrom(LEGACY_HISTORY_STORAGE_KEY)

    override suspend fun readHistory(sessionId: String): ChatHistoryDataModel = readHistoryFrom(sessionStorageKey(sessionId))

    override suspend fun writeHistory(sessionId: String, history: ChatHistoryDataModel) = withContext(ioDispatcher) {
        localStorage[sessionStorageKey(sessionId)] = json.encodeToString(history)
    }

    override suspend fun deleteHistory(sessionId: String) = withContext(ioDispatcher) {
        localStorage.removeItem(sessionStorageKey(sessionId))
    }

    override suspend fun writeExport(history: ChatHistoryDataModel): String = withContext(ioDispatcher) {
        localStorage[EXPORT_STORAGE_KEY] = json.encodeToString(history)
        EXPORT_STORAGE_KEY
    }

    override fun parseHistory(rawJson: String): ChatHistoryDataModel =
        json.decodeFromString<ChatHistoryDataModel>(rawJson)

    private suspend fun readHistoryFrom(storageKey: String): ChatHistoryDataModel = withContext(ioDispatcher) {
        val content = localStorage[storageKey]
        if (content.isNullOrBlank()) {
            return@withContext emptyHistory()
        }
        runCatching { json.decodeFromString<ChatHistoryDataModel>(content) }.getOrElse { emptyHistory() }
    }

    private fun sessionStorageKey(sessionId: String): String = "$SESSION_HISTORY_STORAGE_KEY_PREFIX$sessionId"

    private fun emptyHistory(): ChatHistoryDataModel =
        ChatHistoryDataModel(version = HISTORY_VERSION, messages = emptyList())
}
