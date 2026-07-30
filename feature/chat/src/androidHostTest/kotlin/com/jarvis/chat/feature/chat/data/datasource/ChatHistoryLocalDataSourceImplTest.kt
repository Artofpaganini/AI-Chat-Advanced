package com.jarvis.chat.feature.chat.data.datasource

import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.model.ChatMessageDataModel
import com.jarvis.chat.feature.chat.data.model.ChatSessionDataModel
import com.jarvis.chat.feature.chat.data.model.ChatSessionsIndexDataModel
import com.jarvis.chat.feature.chat.domain.model.ChatStorageConfigModel
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import kotlinx.io.buffered
import kotlinx.io.files.Path
import kotlinx.io.files.SystemFileSystem
import kotlinx.io.writeString
import kotlinx.serialization.SerializationException
import kotlin.random.Random
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNull
import kotlin.test.assertTrue

class ChatHistoryLocalDataSourceImplTest {

    @Test
    fun readLegacyHistory_whenFileMissing_returnsEmptyVersionedHistory() = runTest {
        val dataSource = createDataSource(uniqueDirectory())

        val history = dataSource.readLegacyHistory()

        assertEquals(1, history.version)
        assertTrue(history.messages.isEmpty())
    }

    @Test
    fun readHistory_whenSessionFileMissing_returnsEmptyVersionedHistory() = runTest {
        val dataSource = createDataSource(uniqueDirectory())

        val history = dataSource.readHistory("session-1")

        assertEquals(1, history.version)
        assertTrue(history.messages.isEmpty())
    }

    @Test
    fun writeHistory_thenReadHistory_roundTripsMessagesForSameSession() = runTest {
        val dataSource = createDataSource(uniqueDirectory())
        val stored = ChatHistoryDataModel(version = 1, messages = listOf(message("a"), message("b")))

        dataSource.writeHistory("session-1", stored)
        val loaded = dataSource.readHistory("session-1")

        assertEquals(stored, loaded)
    }

    @Test
    fun writeHistory_keepsDifferentSessionsIsolated() = runTest {
        val dataSource = createDataSource(uniqueDirectory())
        dataSource.writeHistory("session-1", ChatHistoryDataModel(version = 1, messages = listOf(message("a"))))
        dataSource.writeHistory("session-2", ChatHistoryDataModel(version = 1, messages = listOf(message("b"))))

        val first = dataSource.readHistory("session-1")
        val second = dataSource.readHistory("session-2")

        assertEquals(listOf("a"), first.messages.map { entry -> entry.id })
        assertEquals(listOf("b"), second.messages.map { entry -> entry.id })
    }

    @Test
    fun writeHistory_createsMissingDirectory() = runTest {
        val directory = uniqueDirectory()
        val dataSource = createDataSource(directory)

        dataSource.writeHistory("session-1", ChatHistoryDataModel(version = 1, messages = listOf(message("a"))))

        assertTrue(SystemFileSystem.exists(Path(directory, "chat_history_session-1.json")))
    }

    @Test
    fun deleteHistory_removesSessionFileButKeepsOthers() = runTest {
        val dataSource = createDataSource(uniqueDirectory())
        dataSource.writeHistory("session-1", ChatHistoryDataModel(version = 1, messages = listOf(message("a"))))
        dataSource.writeHistory("session-2", ChatHistoryDataModel(version = 1, messages = listOf(message("b"))))

        dataSource.deleteHistory("session-1")

        assertTrue(dataSource.readHistory("session-1").messages.isEmpty())
        assertEquals(listOf("b"), dataSource.readHistory("session-2").messages.map { entry -> entry.id })
    }

    @Test
    fun deleteHistory_onMissingSession_doesNotThrow() = runTest {
        val dataSource = createDataSource(uniqueDirectory())

        dataSource.deleteHistory("missing-session")
    }

    @Test
    fun readHistory_whenFileIsBlank_returnsEmptyHistory() = runTest {
        val directory = uniqueDirectory()
        writeRawFile(directory, "chat_history_session-1.json", "   ")
        val dataSource = createDataSource(directory)

        val history = dataSource.readHistory("session-1")

        assertTrue(history.messages.isEmpty())
    }

    @Test
    fun readHistory_whenFileIsCorrupted_returnsEmptyHistoryInsteadOfThrowing() = runTest {
        val directory = uniqueDirectory()
        writeRawFile(directory, "chat_history_session-1.json", "{ this is not json ]")
        val dataSource = createDataSource(directory)

        val history = dataSource.readHistory("session-1")

        assertEquals(1, history.version)
        assertTrue(history.messages.isEmpty())
    }

    @Test
    fun readSessionsIndex_whenFileMissing_returnsNull() = runTest {
        val dataSource = createDataSource(uniqueDirectory())

        assertNull(dataSource.readSessionsIndex())
    }

    @Test
    fun writeSessionsIndex_thenReadSessionsIndex_roundTrips() = runTest {
        val dataSource = createDataSource(uniqueDirectory())
        val index = ChatSessionsIndexDataModel(
            version = 1,
            sessions = listOf(
                ChatSessionDataModel(id = "session-1", title = "Trip plan", createdAt = 1L, lastMessageAt = 2L, messageCount = 3),
            ),
            activeSessionId = "session-1",
        )

        dataSource.writeSessionsIndex(index)
        val loaded = dataSource.readSessionsIndex()

        assertEquals(index, loaded)
    }

    @Test
    fun readSessionsIndex_whenFileIsCorrupted_returnsNull() = runTest {
        val directory = uniqueDirectory()
        writeRawFile(directory, "chat_sessions.json", "{ not json ]")
        val dataSource = createDataSource(directory)

        assertNull(dataSource.readSessionsIndex())
    }

    @Test
    fun writeExport_returnsPathAndWritesParsableContent() = runTest {
        val dataSource = createDataSource(uniqueDirectory())
        val stored = ChatHistoryDataModel(version = 1, messages = listOf(message("exported")))

        val path = dataSource.writeExport(stored)

        assertTrue(path.endsWith("chat_history_export.json"), "unexpected path: $path")
        assertTrue(SystemFileSystem.exists(Path(path)))
    }

    @Test
    fun writeExport_doesNotOverwriteSessionHistoryFile() = runTest {
        val directory = uniqueDirectory()
        val dataSource = createDataSource(directory)
        dataSource.writeHistory("session-1", ChatHistoryDataModel(version = 1, messages = listOf(message("kept"))))

        dataSource.writeExport(ChatHistoryDataModel(version = 1, messages = listOf(message("other"))))

        assertEquals("kept", dataSource.readHistory("session-1").messages.single().id)
    }

    @Test
    fun parseHistory_onInvalidJson_throwsSerializationException() {
        val dataSource = createDataSource(uniqueDirectory())

        assertFailsWith<SerializationException> { dataSource.parseHistory("not json at all") }
    }

    private fun createDataSource(directoryPath: String): ChatHistoryLocalDataSourceImpl =
        ChatHistoryLocalDataSourceImpl(
            storageConfig = ChatStorageConfigModel(directoryPath = directoryPath),
            ioDispatcher = UnconfinedTestDispatcher(),
        )

    private fun uniqueDirectory(): String = "build/tmp/chat-history-test-${Random.nextLong()}"

    private fun writeRawFile(directoryPath: String, fileName: String, content: String) {
        val directory = Path(directoryPath)
        if (!SystemFileSystem.exists(directory)) {
            SystemFileSystem.createDirectories(directory)
        }
        SystemFileSystem.sink(Path(directoryPath, fileName)).buffered()
            .use { sink -> sink.writeString(content) }
    }

    private fun message(id: String): ChatMessageDataModel =
        ChatMessageDataModel(id = id, author = "USER", text = "text-$id", isFavorite = false)
}
