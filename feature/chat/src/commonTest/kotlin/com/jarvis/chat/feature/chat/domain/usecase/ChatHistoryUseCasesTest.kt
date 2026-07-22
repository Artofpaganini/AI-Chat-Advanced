package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class ChatHistoryUseCasesTest {

    @Test
    fun load_returnsRepositoryMessages() = runTest {
        val stored = listOf(message(id = "m1"))
        val repository = FakeChatHistoryRepository(initial = stored)

        val loaded = LoadChatHistoryUseCase(repository).invoke()

        assertEquals(stored, loaded)
    }

    @Test
    fun save_onSuccess_returnsUnitAndPersists() = runTest {
        val repository = FakeChatHistoryRepository()
        val messages = listOf(message(id = "m1"))

        val result = SaveChatHistoryUseCase(repository).invoke(messages)

        assertTrue(result.isSuccess)
        assertEquals(messages, repository.loadMessages())
    }

    @Test
    fun save_onRepositoryFailure_returnsFailureAndDoesNotThrow() = runTest {
        val repository = FakeChatHistoryRepository(shouldFail = true)

        val result = SaveChatHistoryUseCase(repository).invoke(listOf(message(id = "m1")))

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
            .invoke(json = "{}", strategy = ImportStrategy.MERGE, current = emptyList())

        assertEquals(merged, result.getOrNull())
        assertEquals(ImportStrategy.MERGE, repository.lastImportStrategy)
    }

    @Test
    fun import_onRepositoryFailure_returnsFailure() = runTest {
        val repository = FakeChatHistoryRepository(shouldFail = true)

        val result = ImportChatHistoryUseCase(repository)
            .invoke(json = "broken", strategy = ImportStrategy.REPLACE, current = emptyList())

        assertTrue(result.isFailure)
    }

    private fun message(id: String): HistoryMessageModel =
        HistoryMessageModel(id = id, author = MessageAuthor.USER, text = "text", isFavorite = false)
}

private class FakeChatHistoryRepository(
    initial: List<HistoryMessageModel> = emptyList(),
    private val shouldFail: Boolean = false,
    private val exportPath: String = "fake://export.json",
    private val importResult: List<HistoryMessageModel> = emptyList(),
) : ChatHistoryRepository {

    private var messages = initial

    var lastImportStrategy: ImportStrategy? = null
        private set

    override suspend fun loadMessages(): List<HistoryMessageModel> = messages

    override suspend fun saveMessages(messages: List<HistoryMessageModel>) {
        failIfRequested()
        this.messages = messages
    }

    override suspend fun exportMessages(messages: List<HistoryMessageModel>): String {
        failIfRequested()
        return exportPath
    }

    override suspend fun importMessages(
        json: String,
        strategy: ImportStrategy,
        current: List<HistoryMessageModel>,
    ): List<HistoryMessageModel> {
        failIfRequested()
        lastImportStrategy = strategy
        messages = importResult
        return importResult
    }

    private fun failIfRequested() {
        if (shouldFail) {
            throw IllegalStateException("fake repository failure")
        }
    }
}
