package com.jarvis.chat.feature.chat.data.repository

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.data.datasource.ChatHistoryLocalDataSource
import com.jarvis.chat.feature.chat.data.mapper.toChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.mapper.toChatSessionModel
import com.jarvis.chat.feature.chat.data.mapper.toChatSessionsModel
import com.jarvis.chat.feature.chat.data.mapper.toHistoryMessageModel
import com.jarvis.chat.feature.chat.data.model.ChatSessionDataModel
import com.jarvis.chat.feature.chat.data.model.ChatSessionsIndexDataModel
import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel
import com.jarvis.chat.feature.chat.domain.model.ChatSessionsModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlin.random.Random
import kotlin.time.Clock

private const val SESSIONS_INDEX_VERSION = 1
private const val SESSION_ID_PREFIX = "session-"
private const val TITLE_WORD_COUNT = 6

internal class ChatHistoryRepositoryImpl(
    private val localDataSource: ChatHistoryLocalDataSource,
) : ChatHistoryRepository {

    private val activeSessionIdFlow = MutableStateFlow<String?>(null)

    override fun observeActiveSessionId(): StateFlow<String?> = activeSessionIdFlow.asStateFlow()

    override suspend fun loadSessions(): ChatSessionsModel {
        val index = currentIndex()
        activeSessionIdFlow.update { index.activeSessionId }
        return index.toChatSessionsModel()
    }

    override suspend fun createSession(): ChatSessionModel {
        val index = currentIndex()
        val now = Clock.System.now().toEpochMilliseconds()
        val newSession = ChatSessionDataModel(
            id = newSessionId(),
            title = "",
            createdAt = now,
            lastMessageAt = now,
            messageCount = 0,
        )
        localDataSource.writeHistory(newSession.id, emptyHistoryDataModel())
        val updatedIndex = index.copy(sessions = index.sessions + newSession, activeSessionId = newSession.id)
        localDataSource.writeSessionsIndex(updatedIndex)
        activeSessionIdFlow.update { newSession.id }
        return newSession.toChatSessionModel()
    }

    override suspend fun renameSession(sessionId: String, title: String) {
        val index = currentIndex()
        val updatedSessions = index.sessions.map { session ->
            if (session.id == sessionId) session.copy(title = title) else session
        }
        localDataSource.writeSessionsIndex(index.copy(sessions = updatedSessions))
    }

    override suspend fun deleteSession(sessionId: String): ChatSessionsModel {
        val index = currentIndex()
        localDataSource.deleteHistory(sessionId)
        val remainingSessions = index.sessions.filterNot { session -> session.id == sessionId }
        val finalSessions = if (remainingSessions.isEmpty()) {
            val fallbackSession = defaultSessionDataModel()
            localDataSource.writeHistory(fallbackSession.id, emptyHistoryDataModel())
            listOf(fallbackSession)
        } else {
            remainingSessions
        }
        val newActiveSessionId = if (index.activeSessionId == sessionId) {
            finalSessions.maxBy { session -> session.lastMessageAt }.id
        } else {
            index.activeSessionId
        }
        val updatedIndex = index.copy(sessions = finalSessions, activeSessionId = newActiveSessionId)
        localDataSource.writeSessionsIndex(updatedIndex)
        activeSessionIdFlow.update { newActiveSessionId }
        return updatedIndex.toChatSessionsModel()
    }

    override suspend fun switchSession(sessionId: String) {
        val index = currentIndex()
        if (index.sessions.none { session -> session.id == sessionId }) {
            return
        }
        localDataSource.writeSessionsIndex(index.copy(activeSessionId = sessionId))
        activeSessionIdFlow.update { sessionId }
    }

    override suspend fun loadMessages(sessionId: String): List<HistoryMessageModel> =
        localDataSource.readHistory(sessionId).messages.map { message -> message.toHistoryMessageModel() }

    override suspend fun saveMessages(sessionId: String, messages: List<HistoryMessageModel>) {
        localDataSource.writeHistory(sessionId, messages.toChatHistoryDataModel())
        touchSession(sessionId, messages)
    }

    override suspend fun clearMessages(sessionId: String) {
        saveMessages(sessionId, emptyList())
    }

    override suspend fun exportMessages(messages: List<HistoryMessageModel>): String =
        localDataSource.writeExport(messages.toChatHistoryDataModel())

    override suspend fun importMessages(
        sessionId: String,
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
        saveMessages(sessionId, result)
        return result
    }

    private suspend fun currentIndex(): ChatSessionsIndexDataModel =
        localDataSource.readSessionsIndex() ?: migrateLegacyHistory()

    private suspend fun migrateLegacyHistory(): ChatSessionsIndexDataModel {
        val legacy = localDataSource.readLegacyHistory()
        val defaultSession = defaultSessionDataModel(legacy.messages.map { message -> message.toHistoryMessageModel() })
        localDataSource.writeHistory(defaultSession.id, legacy)
        val index = ChatSessionsIndexDataModel(
            version = SESSIONS_INDEX_VERSION,
            sessions = listOf(defaultSession),
            activeSessionId = defaultSession.id,
        )
        localDataSource.writeSessionsIndex(index)
        return index
    }

    private suspend fun touchSession(sessionId: String, messages: List<HistoryMessageModel>) {
        val index = localDataSource.readSessionsIndex() ?: return
        val session = index.sessions.find { existingSession -> existingSession.id == sessionId } ?: return
        val updatedSession = session.copy(
            title = session.title.ifBlank { deriveTitle(messages) },
            lastMessageAt = messages.lastOrNull()?.timestamp ?: session.lastMessageAt,
            messageCount = messages.size,
        )
        val updatedSessions = index.sessions.map { existingSession ->
            if (existingSession.id == sessionId) updatedSession else existingSession
        }
        localDataSource.writeSessionsIndex(index.copy(sessions = updatedSessions))
    }

    private fun deriveTitle(messages: List<HistoryMessageModel>): String {
        val firstUserMessage = messages.firstOrNull { message -> message.author == MessageAuthor.USER } ?: return ""
        return firstUserMessage.text.trim()
            .split(Regex("\\s+"))
            .filter { word -> word.isNotBlank() }
            .take(TITLE_WORD_COUNT)
            .joinToString(" ")
    }

    private fun defaultSessionDataModel(messages: List<HistoryMessageModel> = emptyList()): ChatSessionDataModel {
        val now = Clock.System.now().toEpochMilliseconds()
        return ChatSessionDataModel(
            id = newSessionId(),
            title = deriveTitle(messages),
            createdAt = messages.firstOrNull()?.timestamp ?: now,
            lastMessageAt = messages.lastOrNull()?.timestamp ?: now,
            messageCount = messages.size,
        )
    }

    private fun newSessionId(): String = "$SESSION_ID_PREFIX${Clock.System.now().toEpochMilliseconds()}-${Random.nextLong()}"

    private fun emptyHistoryDataModel() = emptyList<HistoryMessageModel>().toChatHistoryDataModel()

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
