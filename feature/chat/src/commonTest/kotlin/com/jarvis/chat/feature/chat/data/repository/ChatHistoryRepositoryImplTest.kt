package com.jarvis.chat.feature.chat.data.repository

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.data.datasource.ChatHistoryLocalDataSource
import com.jarvis.chat.feature.chat.data.mapper.toChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.mapper.toHistoryMessageModel
import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.model.ChatSessionsIndexDataModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotEquals
import kotlin.test.assertTrue

private const val EMPTY_HISTORY_VERSION = 1

class ChatHistoryRepositoryImplTest {

    private val dataSource = FakeChatHistoryLocalDataSource()
    private val repository = ChatHistoryRepositoryImpl(localDataSource = dataSource)

    @Test
    fun saveThenLoad_returnsSameMessagesForSameSession() = runTest {
        val messages = listOf(
            userMessage(id = "u1", text = "hi"),
            assistantMessage(id = "a1", text = "hello", isFavorite = true),
        )

        repository.saveMessages("session-1", messages)
        val loaded = repository.loadMessages("session-1")

        assertEquals(messages, loaded)
    }

    @Test
    fun load_onEmptyDataSource_returnsEmpty() = runTest {
        val loaded = repository.loadMessages("session-1")

        assertEquals(emptyList(), loaded)
    }

    @Test
    fun messagesOfDifferentSessions_doNotMix() = runTest {
        val firstSessionMessages = listOf(userMessage(id = "u1", text = "first session"))
        val secondSessionMessages = listOf(userMessage(id = "u2", text = "second session"))

        repository.saveMessages("session-1", firstSessionMessages)
        repository.saveMessages("session-2", secondSessionMessages)

        assertEquals(firstSessionMessages, repository.loadMessages("session-1"))
        assertEquals(secondSessionMessages, repository.loadMessages("session-2"))
    }

    @Test
    fun loadSessions_onFreshInstall_createsSingleEmptyDefaultSession() = runTest {
        val result = repository.loadSessions()

        assertEquals(1, result.sessions.size)
        assertEquals(result.activeSessionId, result.sessions.single().id)
        assertEquals(0, result.sessions.single().messageCount)
    }

    @Test
    fun loadSessions_withExistingLegacyHistory_migratesMessagesIntoDefaultSession() = runTest {
        val legacyMessages = listOf(
            userMessage(id = "u1", text = "legacy question"),
            assistantMessage(id = "a1", text = "legacy answer", isFavorite = false),
        )
        dataSource.legacyHistory = legacyMessages.toChatHistoryDataModel()

        val result = repository.loadSessions()
        val defaultSessionId = result.activeSessionId

        assertEquals(1, result.sessions.size)
        assertEquals(2, result.sessions.single().messageCount)
        assertEquals(legacyMessages, repository.loadMessages(defaultSessionId))
    }

    @Test
    fun loadSessions_calledTwice_doesNotDuplicateMigration() = runTest {
        dataSource.legacyHistory = listOf(userMessage(id = "u1", text = "legacy")).toChatHistoryDataModel()

        val first = repository.loadSessions()
        val second = repository.loadSessions()

        assertEquals(first.sessions.map { session -> session.id }, second.sessions.map { session -> session.id })
        assertEquals(1, second.sessions.size)
    }

    @Test
    fun createSession_addsNewEmptySessionAndSwitchesActive() = runTest {
        val initial = repository.loadSessions()

        val created = repository.createSession()
        val afterCreate = repository.loadSessions()

        assertEquals(created.id, afterCreate.activeSessionId)
        assertEquals(initial.sessions.size + 1, afterCreate.sessions.size)
        assertEquals(0, created.messageCount)
    }

    @Test
    fun createSession_startsWithBlankTitle() = runTest {
        val created = repository.createSession()

        assertEquals("", created.title)
    }

    @Test
    fun saveMessages_deriveTitleFromFirstUserMessage() = runTest {
        val session = repository.createSession()

        repository.saveMessages(
            session.id,
            listOf(userMessage(id = "u1", text = "How do I plan a trip to Rome"), assistantMessage(id = "a1", text = "Sure", isFavorite = false)),
        )

        val updated = repository.loadSessions().sessions.first { existing -> existing.id == session.id }
        assertEquals("How do I plan a trip", updated.title)
    }

    @Test
    fun saveMessages_doesNotOverwriteAlreadySetTitle() = runTest {
        val session = repository.createSession()
        repository.renameSession(session.id, "Custom title")

        repository.saveMessages(session.id, listOf(userMessage(id = "u1", text = "some question")))

        val updated = repository.loadSessions().sessions.first { existing -> existing.id == session.id }
        assertEquals("Custom title", updated.title)
    }

    @Test
    fun switchSession_updatesActiveSessionIdAndObservableFlow() = runTest {
        repository.loadSessions()
        val created = repository.createSession()
        val other = repository.createSession()

        repository.switchSession(created.id)

        assertEquals(created.id, repository.observeActiveSessionId().value)
        assertNotEquals(other.id, repository.observeActiveSessionId().value)
    }

    @Test
    fun renameSession_updatesTitle() = runTest {
        val session = repository.createSession()

        repository.renameSession(session.id, "Renamed chat")

        val updated = repository.loadSessions().sessions.first { existing -> existing.id == session.id }
        assertEquals("Renamed chat", updated.title)
    }

    @Test
    fun deleteSession_removesItAndSwitchesToAnotherSession() = runTest {
        val first = repository.loadSessions().sessions.single()
        val second = repository.createSession()
        repository.switchSession(second.id)

        val result = repository.deleteSession(second.id)

        assertEquals(listOf(first.id), result.sessions.map { session -> session.id })
        assertEquals(first.id, result.activeSessionId)
    }

    @Test
    fun deleteSession_whenLastRemainingSession_createsFreshDefaultSession() = runTest {
        val onlySession = repository.loadSessions().sessions.single()

        val result = repository.deleteSession(onlySession.id)

        assertEquals(1, result.sessions.size)
        assertNotEquals(onlySession.id, result.sessions.single().id)
        assertEquals(0, result.sessions.single().messageCount)
    }

    @Test
    fun deleteSession_removesItsMessages() = runTest {
        val session = repository.createSession()
        repository.saveMessages(session.id, listOf(userMessage(id = "u1", text = "will be deleted")))

        repository.deleteSession(session.id)

        assertTrue(repository.loadMessages(session.id).isEmpty())
    }

    @Test
    fun export_returnsPathAndWritesRoundTrippableContent() = runTest {
        val messages = listOf(assistantMessage(id = "a1", text = "answer", isFavorite = false))

        val path = repository.exportMessages(messages)

        assertEquals(FakeChatHistoryLocalDataSource.EXPORT_PATH, path)
        val exported = dataSource.parseHistory(dataSource.lastExportedContent.orEmpty())
        val restored = exported.messages.map { message -> message.toHistoryMessageModel() }
        assertEquals(messages, restored)
    }

    @Test
    fun importReplace_returnsImportedAndPersistsThemIntoTargetSession() = runTest {
        val current = listOf(userMessage(id = "u1", text = "old"))
        val imported = listOf(assistantMessage(id = "a1", text = "new", isFavorite = false))
        val json = encodeHistory(imported)

        val result = repository.importMessages(sessionId = "session-1", json = json, strategy = ImportStrategy.REPLACE, current = current)

        assertEquals(imported, result)
        assertEquals(imported, repository.loadMessages("session-1"))
    }

    @Test
    fun importMerge_replacesByIdKeepsCurrentOrderAndAppendsNew() = runTest {
        val current = listOf(
            assistantMessage(id = "a1", text = "kept", isFavorite = true),
            userMessage(id = "u1", text = "stays"),
        )
        val imported = listOf(
            userMessage(id = "u1", text = "updated"),
            assistantMessage(id = "a2", text = "added", isFavorite = false),
        )
        val json = encodeHistory(imported)

        val result = repository.importMessages(sessionId = "session-1", json = json, strategy = ImportStrategy.MERGE, current = current)

        assertEquals(listOf("a1", "u1", "a2"), result.map { message -> message.id })
        assertEquals("updated", result.first { message -> message.id == "u1" }.text)
        assertEquals(result, repository.loadMessages("session-1"))
    }

    @Test
    fun import_invalidJson_propagatesSerializationError() = runTest {
        assertFailsWith<SerializationException> {
            repository.importMessages(sessionId = "session-1", json = "{ not json", strategy = ImportStrategy.MERGE, current = emptyList())
        }
    }

    private fun encodeHistory(messages: List<HistoryMessageModel>): String =
        Json.encodeToString(messages.toChatHistoryDataModel())

    private fun userMessage(id: String, text: String): HistoryMessageModel =
        HistoryMessageModel(
            id = id,
            author = MessageAuthor.USER,
            text = text,
            isFavorite = false,
            timestamp = TEST_TIMESTAMP,
        )

    private fun assistantMessage(id: String, text: String, isFavorite: Boolean): HistoryMessageModel =
        HistoryMessageModel(
            id = id,
            author = MessageAuthor.ASSISTANT,
            text = text,
            isFavorite = isFavorite,
            timestamp = TEST_TIMESTAMP,
        )
}

private const val TEST_TIMESTAMP = 1_700_000_000_000L

private class FakeChatHistoryLocalDataSource : ChatHistoryLocalDataSource {

    private val json = Json { ignoreUnknownKeys = true }

    private val sessionHistories = mutableMapOf<String, ChatHistoryDataModel>()
    private var sessionsIndex: ChatSessionsIndexDataModel? = null

    var legacyHistory: ChatHistoryDataModel? = null

    var lastExportedContent: String? = null
        private set

    override suspend fun readSessionsIndex(): ChatSessionsIndexDataModel? = sessionsIndex

    override suspend fun writeSessionsIndex(index: ChatSessionsIndexDataModel) {
        sessionsIndex = index
    }

    override suspend fun readLegacyHistory(): ChatHistoryDataModel =
        legacyHistory ?: ChatHistoryDataModel(version = EMPTY_HISTORY_VERSION, messages = emptyList())

    override suspend fun readHistory(sessionId: String): ChatHistoryDataModel =
        sessionHistories[sessionId] ?: ChatHistoryDataModel(version = EMPTY_HISTORY_VERSION, messages = emptyList())

    override suspend fun writeHistory(sessionId: String, history: ChatHistoryDataModel) {
        sessionHistories[sessionId] = history
    }

    override suspend fun deleteHistory(sessionId: String) {
        sessionHistories.remove(sessionId)
    }

    override suspend fun writeExport(history: ChatHistoryDataModel): String {
        lastExportedContent = json.encodeToString(history)
        return EXPORT_PATH
    }

    override fun parseHistory(rawJson: String): ChatHistoryDataModel = json.decodeFromString(rawJson)

    companion object {
        const val EXPORT_PATH = "fake://chat_history_export.json"
    }
}
