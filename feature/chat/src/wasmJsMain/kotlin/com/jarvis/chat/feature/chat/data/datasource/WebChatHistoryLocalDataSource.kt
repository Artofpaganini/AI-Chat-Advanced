package com.jarvis.chat.feature.chat.data.datasource

import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel
import kotlinx.browser.localStorage
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import org.w3c.dom.get
import org.w3c.dom.set

private const val HISTORY_STORAGE_KEY = "jarvis_chat_history"
private const val EXPORT_STORAGE_KEY = "jarvis_chat_history_export"
private const val HISTORY_VERSION = 1

internal class WebChatHistoryLocalDataSource(
    private val ioDispatcher: CoroutineDispatcher,
) : ChatHistoryLocalDataSource {

    private val json: Json = Json {
        ignoreUnknownKeys = true
        prettyPrint = true
    }

    override suspend fun readHistory(): ChatHistoryDataModel = withContext(ioDispatcher) {
        val content = localStorage[HISTORY_STORAGE_KEY]
        if (content.isNullOrBlank()) {
            return@withContext emptyHistory()
        }
        runCatching { json.decodeFromString<ChatHistoryDataModel>(content) }.getOrElse { emptyHistory() }
    }

    override suspend fun writeHistory(history: ChatHistoryDataModel) = withContext(ioDispatcher) {
        localStorage[HISTORY_STORAGE_KEY] = json.encodeToString(history)
    }

    override suspend fun writeExport(history: ChatHistoryDataModel): String = withContext(ioDispatcher) {
        localStorage[EXPORT_STORAGE_KEY] = json.encodeToString(history)
        EXPORT_STORAGE_KEY
    }

    override fun parseHistory(rawJson: String): ChatHistoryDataModel =
        json.decodeFromString<ChatHistoryDataModel>(rawJson)

    private fun emptyHistory(): ChatHistoryDataModel =
        ChatHistoryDataModel(version = HISTORY_VERSION, messages = emptyList())
}
