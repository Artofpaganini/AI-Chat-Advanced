package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel
import com.jarvis.chat.feature.chat.domain.model.ChatSessionsModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

private const val TEST_SESSION_ID = "session-1"

class ChatHistoryUseCasesTest {

    @Test
    fun load_returnsRepositoryMessagesForSession() = runTest {
        val stored = listOf(message(id = "m1"))
        val repository = FakeChatHistoryRepository(initial = stored)

        val loaded = LoadChatHistoryUseCase(repository).invoke(TEST_SESSION_ID)

        assertEquals(stored, loaded)
    }

    @Test
    fun save_onSuccess_returnsUnitAndPersistsToSession() = runTest {
        val repository = FakeChatHistoryRepository()
        val messages = listOf(message(id = "m1"))

        val result = SaveChatHistoryUseCase(repository).invoke(TEST_SESSION_ID, messages)

        assertTrue(result.isSuccess)
        assertEquals(messages, repository.loadMessages(TEST_SESSION_ID))
    }

    @Test
    fun save_onRepositoryFailure_returnsFailureAndDoesNotThrow() = runTest {
        val repository = FakeChatHistoryRepository(shouldFail = true)

        val result = SaveChatHistoryUseCase(repository).invoke(TEST_SESSION_ID, listOf(message(id = "m1")))

        assertTrue(result.isFailure)
    }

    @Test
    fun export_onSuccess_returnsPath() = runTest {
        val repository = FakeChatHistoryRepository(exportPath = "path://export.json")

        val result = ExportChatHistoryUseCase(repository).invoke(listOf(message(id = "m1")))

        assertEquals("path://export.json", result.getOrNull())
    }

    @Test
    fun export_onRepositoryFailure_returnsFailure() = runTest {
        val repository = FakeChatHistoryRepository(shouldFail = true)

        val result = ExportChatHistoryUseCase(repository).invoke(listOf(message(id = "m1")))

        assertTrue(result.isFailure)
    }

    @Test
    fun import_onSuccess_returnsMergedListAndForwardsStrategy() = runTest {
        val merged = listOf(message(id = "m1"), message(id = "m2"))
        val repository = FakeChatHistoryRepository(importResult = merged)

        val result = ImportChatHistoryUseCase(repository)
            .invoke(sessionId = TEST_SESSION_ID, json = "{}", strategy = ImportStrategy.MERGE, current = emptyList())

        assertEquals(merged, result.getOrNull())
        assertEquals(ImportStrategy.MERGE, repository.lastImportStrategy)
        assertEquals(TEST_SESSION_ID, repository.lastImportSessionId)
    }

    @Test
    fun import_onRepositoryFailure_returnsFailure() = runTest {
        val repository = FakeChatHistoryRepository(shouldFail = true)

        val result = ImportChatHistoryUseCase(repository)
            .invoke(sessionId = TEST_SESSION_ID, json = "broken", strategy = ImportStrategy.REPLACE, current = emptyList())

        assertTrue(result.isFailure)
    }

    @Test
    fun delete_removesTargetMessageAndKeepsSiblings() = runTest {
        val repository = FakeChatHistoryRepository()
        val messages = listOf(message(id = "m1"), message(id = "m2"), message(id = "m3"))

        val result = DeleteMessageUseCase(repository).invoke(sessionId = TEST_SESSION_ID, messages = messages, messageId = "m2")

        assertEquals(listOf("m1", "m3"), result.getOrNull()?.map { deletedMessage -> deletedMessage.id })
    }

    @Test
    fun delete_onSuccess_persistsUpdatedHistoryToSession() = runTest {
        val repository = FakeChatHistoryRepository()
        val messages = listOf(message(id = "m1"), message(id = "m2"))

        DeleteMessageUseCase(repository).invoke(sessionId = TEST_SESSION_ID, messages = messages, messageId = "m1")

        assertEquals(listOf("m2"), repository.loadMessages(TEST_SESSION_ID).map { savedMessage -> savedMessage.id })
    }

    @Test
    fun delete_onRepositoryFailure_returnsFailure() = runTest {
        val repository = FakeChatHistoryRepository(shouldFail = true)

        val result = DeleteMessageUseCase(repository)
            .invoke(sessionId = TEST_SESSION_ID, messages = listOf(message(id = "m1")), messageId = "m1")

        assertTrue(result.isFailure)
    }

    @Test
    fun clear_onSuccess_emptiesSessionMessages() = runTest {
        val repository = FakeChatHistoryRepository(initial = listOf(message(id = "m1")))

        val result = ClearChatHistoryUseCase(repository).invoke(TEST_SESSION_ID)

        assertTrue(result.isSuccess)
        assertTrue(repository.loadMessages(TEST_SESSION_ID).isEmpty())
    }

    @Test
    fun createSession_onSuccess_returnsCreatedSession() = runTest {
        val repository = FakeChatHistoryRepository()

        val result = CreateChatSessionUseCase(repository).invoke()

        assertTrue(result.isSuccess)
        assertEquals(repository.createdSessionId, result.getOrNull()?.id)
    }

    @Test
    fun switchSession_onSuccess_forwardsSessionId() = runTest {
        val repository = FakeChatHistoryRepository()

        val result = SwitchChatSessionUseCase(repository).invoke(TEST_SESSION_ID)

        assertTrue(result.isSuccess)
        assertEquals(TEST_SESSION_ID, repository.lastSwitchedSessionId)
    }

    @Test
    fun renameSession_onSuccess_forwardsTitle() = runTest {
        val repository = FakeChatHistoryRepository()

        val result = RenameChatSessionUseCase(repository).invoke(TEST_SESSION_ID, "New title")

        assertTrue(result.isSuccess)
        assertEquals("New title", repository.lastRenameTitle)
    }

    @Test
    fun deleteSession_onSuccess_returnsUpdatedSessionsModel() = runTest {
        val repository = FakeChatHistoryRepository(
            deleteResult = ChatSessionsModel(sessions = emptyList(), activeSessionId = "session-2"),
        )

        val result = DeleteChatSessionUseCase(repository).invoke(TEST_SESSION_ID)

        assertEquals("session-2", result.getOrNull()?.activeSessionId)
    }

    private fun message(id: String): HistoryMessageModel =
        HistoryMessageModel(
            id = id,
            author = MessageAuthor.USER,
            text = "text",
            isFavorite = false,
            timestamp = TEST_TIMESTAMP,
        )
}

private const val TEST_TIMESTAMP = 1_700_000_000_000L

private class FakeChatHistoryRepository(
    initial: List<HistoryMessageModel> = emptyList(),
    private val shouldFail: Boolean = false,
    private val exportPath: String = "fake://export.json",
    private val importResult: List<HistoryMessageModel> = emptyList(),
    private val deleteResult: ChatSessionsModel = ChatSessionsModel(sessions = emptyList(), activeSessionId = ""),
) : ChatHistoryRepository {

    private val messagesBySession = mutableMapOf(TEST_SESSION_ID to initial)
    private val activeSessionIdFlow = MutableStateFlow<String?>(null)

    var lastImportStrategy: ImportStrategy? = null
        private set
    var lastImportSessionId: String? = null
        private set
    var lastSwitchedSessionId: String? = null
        private set
    var lastRenameTitle: String? = null
        private set
    var createdSessionId: String? = null
        private set

    override fun observeActiveSessionId(): StateFlow<String?> = activeSessionIdFlow

    override suspend fun loadSessions(): ChatSessionsModel {
        failIfRequested()
        return ChatSessionsModel(sessions = emptyList(), activeSessionId = "")
    }

    override suspend fun createSession(): ChatSessionModel {
        failIfRequested()
        createdSessionId = "created-session"
        return ChatSessionModel(id = "created-session", title = "", createdAt = 0L, lastMessageAt = 0L, messageCount = 0)
    }

    override suspend fun renameSession(sessionId: String, title: String) {
        failIfRequested()
        lastRenameTitle = title
    }

    override suspend fun deleteSession(sessionId: String): ChatSessionsModel {
        failIfRequested()
        return deleteResult
    }

    override suspend fun switchSession(sessionId: String) {
        failIfRequested()
        lastSwitchedSessionId = sessionId
    }

    override suspend fun loadMessages(sessionId: String): List<HistoryMessageModel> = messagesBySession[sessionId].orEmpty()

    override suspend fun saveMessages(sessionId: String, messages: List<HistoryMessageModel>) {
        failIfRequested()
        messagesBySession[sessionId] = messages
    }

    override suspend fun clearMessages(sessionId: String) {
        failIfRequested()
        messagesBySession[sessionId] = emptyList()
    }

    override suspend fun exportMessages(messages: List<HistoryMessageModel>): String {
        failIfRequested()
        return exportPath
    }

    override suspend fun importMessages(
        sessionId: String,
        json: String,
        strategy: ImportStrategy,
        current: List<HistoryMessageModel>,
    ): List<HistoryMessageModel> {
        failIfRequested()
        lastImportStrategy = strategy
        lastImportSessionId = sessionId
        messagesBySession[sessionId] = importResult
        return importResult
    }

    private fun failIfRequested() {
        if (shouldFail) {
            error("fake repository failure")
        }
    }
}
