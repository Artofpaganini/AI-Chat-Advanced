package com.jarvis.chat.feature.chat.data.repository

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.data.datasource.ChatHistoryLocalDataSource
import com.jarvis.chat.feature.chat.data.mapper.toChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.mapper.toHistoryMessageModel
import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

private const val EMPTY_HISTORY_VERSION = 1

class ChatHistoryRepositoryImplTest {

    private val dataSource = FakeChatHistoryLocalDataSource()
    private val repository = ChatHistoryRepositoryImpl(localDataSource = dataSource)

    @Test
    fun saveThenLoad_returnsSameMessages() = runTest {
        val messages = listOf(
            userMessage(id = "u1", text = "hi"),
            assistantMessage(id = "a1", text = "hello", isFavorite = true),
        )

        repository.saveMessages(messages)
        val loaded = repository.loadMessages()

        assertEquals(messages, loaded)
    }

    @Test
    fun load_onEmptyDataSource_returnsEmpty() = runTest {
        val loaded = repository.loadMessages()

        assertEquals(emptyList(), loaded)
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
    fun importReplace_returnsImportedAndPersistsThem() = runTest {
        val current = listOf(userMessage(id = "u1", text = "old"))
        val imported = listOf(assistantMessage(id = "a1", text = "new", isFavorite = false))
        val json = encodeHistory(imported)

        val result = repository.importMessages(json = json, strategy = ImportStrategy.REPLACE, current = current)

        assertEquals(imported, result)
        assertEquals(imported, repository.loadMessages())
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

        val result = repository.importMessages(json = json, strategy = ImportStrategy.MERGE, current = current)

        assertEquals(listOf("a1", "u1", "a2"), result.map { message -> message.id })
        assertEquals("updated", result.first { message -> message.id == "u1" }.text)
        assertEquals(result, repository.loadMessages())
    }

    @Test
    fun importMerge_withEmptyCurrent_equalsImported() = runTest {
        val imported = listOf(assistantMessage(id = "a1", text = "solo", isFavorite = false))
        val json = encodeHistory(imported)

        val result = repository.importMessages(json = json, strategy = ImportStrategy.MERGE, current = emptyList())

        assertEquals(imported, result)
    }

    @Test
    fun import_invalidJson_propagatesSerializationError() = runTest {
        assertFailsWith<SerializationException> {
            repository.importMessages(json = "{ not json", strategy = ImportStrategy.MERGE, current = emptyList())
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

    private var stored = ChatHistoryDataModel(version = EMPTY_HISTORY_VERSION, messages = emptyList())

    var lastExportedContent: String? = null
        private set

    override suspend fun readHistory(): ChatHistoryDataModel = stored

    override suspend fun writeHistory(history: ChatHistoryDataModel) {
        stored = history
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
