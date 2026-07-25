package com.jarvis.chat.feature.chat.data.datasource

import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.model.ChatMessageDataModel
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
import kotlin.test.assertTrue

class ChatHistoryLocalDataSourceImplTest {

    @Test
    fun readHistory_whenFileMissing_returnsEmptyVersionedHistory() = runTest {
        val dataSource = createDataSource(uniqueDirectory())

        val history = dataSource.readHistory()

        assertEquals(1, history.version)
        assertTrue(history.messages.isEmpty())
    }

    @Test
    fun writeHistory_thenReadHistory_roundTripsMessages() = runTest {
        val dataSource = createDataSource(uniqueDirectory())
        val stored = ChatHistoryDataModel(version = 1, messages = listOf(message("a"), message("b")))

        dataSource.writeHistory(stored)
        val loaded = dataSource.readHistory()

        assertEquals(stored, loaded)
    }

    @Test
    fun writeHistory_createsMissingDirectory() = runTest {
        val directory = uniqueDirectory()
        val dataSource = createDataSource(directory)

        dataSource.writeHistory(ChatHistoryDataModel(version = 1, messages = listOf(message("a"))))

        assertTrue(SystemFileSystem.exists(Path(directory, "chat_history.json")))
    }

    @Test
    fun readHistory_whenFileIsBlank_returnsEmptyHistory() = runTest {
        val directory = uniqueDirectory()
        writeRawHistory(directory, "   ")
        val dataSource = createDataSource(directory)

        val history = dataSource.readHistory()

        assertTrue(history.messages.isEmpty())
    }

    @Test
    fun readHistory_whenFileIsCorrupted_returnsEmptyHistoryInsteadOfThrowing() = runTest {
        val directory = uniqueDirectory()
        writeRawHistory(directory, "{ this is not json ]")
        val dataSource = createDataSource(directory)

        val history = dataSource.readHistory()

        assertEquals(1, history.version)
        assertTrue(history.messages.isEmpty())
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
    fun writeExport_doesNotOverwriteHistoryFile() = runTest {
        val directory = uniqueDirectory()
        val dataSource = createDataSource(directory)
        dataSource.writeHistory(ChatHistoryDataModel(version = 1, messages = listOf(message("kept"))))

        dataSource.writeExport(ChatHistoryDataModel(version = 1, messages = listOf(message("other"))))

        assertEquals("kept", dataSource.readHistory().messages.single().id)
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

    private fun writeRawHistory(directoryPath: String, content: String) {
        val directory = Path(directoryPath)
        if (!SystemFileSystem.exists(directory)) {
            SystemFileSystem.createDirectories(directory)
        }
        SystemFileSystem.sink(Path(directoryPath, "chat_history.json")).buffered()
            .use { sink -> sink.writeString(content) }
    }

    private fun message(id: String): ChatMessageDataModel =
        ChatMessageDataModel(id = id, author = "USER", text = "text-$id", isFavorite = false)
}
