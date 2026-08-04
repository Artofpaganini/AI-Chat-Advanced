package com.jarvis.chat.feature.chat.domain.repository

import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel
import com.jarvis.chat.feature.chat.domain.model.ChatSessionsModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportOutcomeModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import kotlinx.coroutines.flow.StateFlow

internal interface ChatHistoryRepository {

    fun observeActiveSessionId(): StateFlow<String?>

    suspend fun loadSessions(): ChatSessionsModel

    suspend fun createSession(): ChatSessionModel

    suspend fun renameSession(sessionId: String, title: String)

    suspend fun deleteSession(sessionId: String): ChatSessionsModel

    suspend fun switchSession(sessionId: String)

    suspend fun loadMessages(sessionId: String): List<HistoryMessageModel>

    suspend fun saveMessages(sessionId: String, messages: List<HistoryMessageModel>)

    suspend fun clearMessages(sessionId: String)

    suspend fun exportMessages(messages: List<HistoryMessageModel>): String

    suspend fun importMessages(
        sessionId: String,
        json: String,
        strategy: ImportStrategy,
        current: List<HistoryMessageModel>,
        isProtectionEnabled: Boolean,
        isTextAllowed: (String) -> Boolean,
    ): ImportOutcomeModel
}
