package com.jarvis.chat.feature.chat.presentation

import app.cash.turbine.test
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageStreamUseCase
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository
import com.jarvis.chat.feature.chat.domain.usecase.ClearChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.DeleteMessageUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ExportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ImportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.SaveChatHistoryUseCase
import com.jarvis.chat.feature.chat.presentation.mapper.ChatUiMapper
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import com.jarvis.chat.feature.chat.presentation.model.ChatEvent
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlin.test.AfterTest
import kotlin.test.BeforeTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class ChatViewModelTest {

    @BeforeTest
    fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
    }

    @AfterTest
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun init_loadsStoredHistoryIntoUiState() = runTest {
        val stored = listOf(historyMessage(id = "1", text = "stored"))
        val viewModel = createViewModel(storedMessages = stored)

        assertEquals(listOf("stored"), viewModel.uiState.value.messages.map { message -> message.text })
    }

    @Test
    fun init_withEmptyStoredHistory_doesNotCrashAndKeepsMessagesEmpty() = runTest {
        val viewModel = createViewModel(storedMessages = emptyList())

        assertTrue(viewModel.uiState.value.messages.isEmpty())
        assertFalse(viewModel.uiState.value.isLoading)
    }

    @Test
    fun inputChanged_updatesInputAndEnablesSend() = runTest {
        val viewModel = createViewModel()

        viewModel.onAction(ChatAction.Ui.InputChanged("hello"))

        assertEquals("hello", viewModel.uiState.value.inputText)
        assertTrue(viewModel.uiState.value.isSendEnabled)
    }

    @Test
    fun inputChanged_withBlankText_keepsSendDisabled() = runTest {
        val viewModel = createViewModel()

        viewModel.onAction(ChatAction.Ui.InputChanged("   "))

        assertFalse(viewModel.uiState.value.isSendEnabled)
    }

    @Test
    fun sendClicked_withBlankInput_doesNotAddMessages() = runTest {
        val viewModel = createViewModel()

        viewModel.onAction(ChatAction.Ui.InputChanged("   "))
        viewModel.onAction(ChatAction.Ui.SendClicked)

        assertTrue(viewModel.uiState.value.messages.isEmpty())
    }

    @Test
    fun sendClicked_appendsUserMessageAndAssistantReply() = runTest {
        val viewModel = createViewModel(reply = "pong")

        viewModel.onAction(ChatAction.Ui.InputChanged("ping"))
        viewModel.onAction(ChatAction.Ui.SendClicked)

        val texts = viewModel.uiState.value.messages.map { message -> message.text }
        assertEquals(listOf("ping", "pong"), texts)
        assertFalse(viewModel.uiState.value.isLoading)
    }

    @Test
    fun sendClicked_clearsInputField() = runTest {
        val viewModel = createViewModel(reply = "pong")

        viewModel.onAction(ChatAction.Ui.InputChanged("ping"))
        viewModel.onAction(ChatAction.Ui.SendClicked)

        assertEquals("", viewModel.uiState.value.inputText)
    }

    @Test
    fun sendClicked_persistsHistory() = runTest {
        val repository = FakeChatHistoryRepository()
        val viewModel = createViewModel(chatRepository = repository, reply = "pong")

        viewModel.onAction(ChatAction.Ui.InputChanged("ping"))
        viewModel.onAction(ChatAction.Ui.SendClicked)

        assertEquals(listOf("ping", "pong"), repository.saved.last().map { message -> message.text })
    }

    @Test
    fun sendClicked_whenRequestFails_showsErrorAndStopsLoading() = runTest {
        val viewModel = createViewModel(aiError = IllegalStateException("no network"))

        viewModel.onAction(ChatAction.Ui.InputChanged("ping"))
        viewModel.onAction(ChatAction.Ui.SendClicked)

        assertTrue(viewModel.uiState.value.isErrorVisible)
        assertFalse(viewModel.uiState.value.isLoading)
        assertEquals(listOf("ping"), viewModel.uiState.value.messages.map { message -> message.text })
    }

    @Test
    fun retryClicked_afterFailure_resendsLastTextAndClearsError() = runTest {
        val aiRepository = FailThenSucceedAiRepository(
            failure = IllegalStateException("no network"),
            successReply = "pong",
        )
        val viewModel = createViewModel(aiRepository = aiRepository)
        viewModel.onAction(ChatAction.Ui.InputChanged("ping"))
        viewModel.onAction(ChatAction.Ui.SendClicked)
        assertTrue(viewModel.uiState.value.isErrorVisible)

        viewModel.onAction(ChatAction.Ui.RetryClicked)

        val texts = viewModel.uiState.value.messages.map { message -> message.text }
        assertEquals(listOf("ping", "pong"), texts)
        assertFalse(viewModel.uiState.value.isErrorVisible)
        assertFalse(viewModel.uiState.value.isLoading)
    }

    @Test
    fun stopClicked_cancelsInFlightRequestAndClearsLoadingWithoutError() = runTest {
        val aiRepository = SuspendingAiRepository()
        val viewModel = createViewModel(aiRepository = aiRepository)

        viewModel.onAction(ChatAction.Ui.InputChanged("ping"))
        viewModel.onAction(ChatAction.Ui.SendClicked)
        assertTrue(viewModel.uiState.value.isLoading)

        viewModel.onAction(ChatAction.Ui.StopClicked)
        advanceUntilIdle()

        assertFalse(viewModel.uiState.value.isLoading)
        assertFalse(viewModel.uiState.value.isErrorVisible)
        assertEquals(listOf("ping"), viewModel.uiState.value.messages.map { message -> message.text })
        assertTrue(aiRepository.wasCancelled)
    }

    @Test
    fun stopClicked_allowsImmediateResend() = runTest {
        val viewModel = createViewModel(aiRepository = SuspendingAiRepository())

        viewModel.onAction(ChatAction.Ui.InputChanged("ping"))
        viewModel.onAction(ChatAction.Ui.SendClicked)
        viewModel.onAction(ChatAction.Ui.StopClicked)

        viewModel.onAction(ChatAction.Ui.InputChanged("second"))
        viewModel.onAction(ChatAction.Ui.SendClicked)

        assertTrue(viewModel.uiState.value.isLoading)
        assertEquals(
            listOf("ping", "second", ""),
            viewModel.uiState.value.messages.map { message -> message.text },
        )
    }

    @Test
    fun sendClicked_joinsMultipleChunksIntoFinalAssistantText() = runTest {
        val viewModel = createViewModel(aiRepository = FakeAiRepository(chunks = listOf("po", "ng")))

        viewModel.onAction(ChatAction.Ui.InputChanged("ping"))
        viewModel.onAction(ChatAction.Ui.SendClicked)

        val texts = viewModel.uiState.value.messages.map { message -> message.text }
        assertEquals(listOf("ping", "pong"), texts)
        assertFalse(viewModel.uiState.value.isLoading)
    }

    @Test
    fun stopClicked_afterPartialChunksArrived_keepsPartialTextWithoutError() = runTest {
        val aiRepository = PartialThenHangingAiRepository()
        val viewModel = createViewModel(aiRepository = aiRepository)

        viewModel.onAction(ChatAction.Ui.InputChanged("ping"))
        viewModel.onAction(ChatAction.Ui.SendClicked)
        viewModel.onAction(ChatAction.Ui.StopClicked)
        advanceUntilIdle()

        assertEquals(
            listOf("ping", "Hello"),
            viewModel.uiState.value.messages.map { message -> message.text },
        )
        assertFalse(viewModel.uiState.value.isLoading)
        assertFalse(viewModel.uiState.value.isErrorVisible)
        assertTrue(aiRepository.wasCancelled)
    }

    @Test
    fun favoriteToggled_flipsFlagForTargetMessageOnly() = runTest {
        val stored = listOf(
            historyMessage(id = "1", text = "one"),
            historyMessage(id = "2", text = "two"),
        )
        val viewModel = createViewModel(storedMessages = stored)

        viewModel.onAction(ChatAction.Ui.FavoriteToggled("2"))

        val favorites = viewModel.uiState.value.messages.filter { message -> message.isFavorite }
        assertEquals(listOf("2"), favorites.map { message -> message.id })
        assertEquals(1, viewModel.uiState.value.favoritesCount)
    }

    @Test
    fun favoriteToggled_twice_returnsToOriginalState() = runTest {
        val viewModel = createViewModel(storedMessages = listOf(historyMessage(id = "1", text = "one")))

        viewModel.onAction(ChatAction.Ui.FavoriteToggled("1"))
        viewModel.onAction(ChatAction.Ui.FavoriteToggled("1"))

        assertEquals(0, viewModel.uiState.value.favoritesCount)
    }

    @Test
    fun favoritesFilterToggled_flipsFilterFlag() = runTest {
        val viewModel = createViewModel()

        viewModel.onAction(ChatAction.Ui.FavoritesFilterToggled)

        assertTrue(viewModel.uiState.value.isFavoritesFilterActive)
    }

    @Test
    fun importRequested_replacesMessagesWithImportedOnes() = runTest {
        val repository = FakeChatHistoryRepository(
            importResult = listOf(historyMessage(id = "9", text = "imported")),
        )
        val viewModel = createViewModel(chatRepository = repository)

        viewModel.onAction(ChatAction.Ui.ImportRequested("{}"))

        assertEquals(listOf("imported"), viewModel.uiState.value.messages.map { message -> message.text })
    }

    @Test
    fun importRequested_usesMergeStrategy() = runTest {
        val repository = FakeChatHistoryRepository(importResult = emptyList())
        val viewModel = createViewModel(chatRepository = repository)

        viewModel.onAction(ChatAction.Ui.ImportRequested("{}"))

        assertEquals(ImportStrategy.MERGE, repository.lastImportStrategy)
    }

    @Test
    fun importRequested_onFailure_showsErrorMessageAndKeepsHistoryIntact() = runTest {
        val repository = FakeChatHistoryRepository(importError = IllegalArgumentException("bad json"))
        val stored = listOf(historyMessage(id = "1", text = "one"))
        val viewModel = createViewModel(storedMessages = stored, chatRepository = repository)

        viewModel.onAction(ChatAction.Ui.ImportRequested("not-json"))

        assertEquals(listOf("one"), viewModel.uiState.value.messages.map { message -> message.text })
        viewModel.events.test {
            assertEquals(ChatEvent.ScrollToBottom, awaitItem())
            assertEquals(ChatEvent.ShowMessage("Import failed. Invalid file."), awaitItem())
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun exportClicked_onSuccess_showsSnackbarWithFilePath() = runTest {
        val repository = FakeChatHistoryRepository(exportResult = "/tmp/history-export.json")
        val viewModel = createViewModel(chatRepository = repository)

        viewModel.onAction(ChatAction.Ui.ExportClicked)

        viewModel.events.test {
            assertEquals(ChatEvent.ScrollToBottom, awaitItem())
            assertEquals(ChatEvent.ShowMessage("History exported to /tmp/history-export.json"), awaitItem())
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun exportClicked_onFailure_showsFailureSnackbar() = runTest {
        val repository = FakeChatHistoryRepository(exportError = IllegalStateException("disk full"))
        val viewModel = createViewModel(chatRepository = repository)

        viewModel.onAction(ChatAction.Ui.ExportClicked)

        viewModel.events.test {
            assertEquals(ChatEvent.ScrollToBottom, awaitItem())
            assertEquals(ChatEvent.ShowMessage("Export failed. Please try again."), awaitItem())
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun suggestionClicked_sendsSuggestionTextAsUserMessage() = runTest {
        val viewModel = createViewModel(reply = "pong")

        viewModel.onAction(ChatAction.Ui.SuggestionClicked("ping"))

        val texts = viewModel.uiState.value.messages.map { message -> message.text }
        assertEquals(listOf("ping", "pong"), texts)
        assertEquals("", viewModel.uiState.value.inputText)
    }

    @Test
    fun voiceTranscribed_fillsInputLikeTyping() = runTest {
        val viewModel = createViewModel()

        viewModel.onAction(ChatAction.Ui.VoiceTranscribed("spoken text"))

        assertEquals("spoken text", viewModel.uiState.value.inputText)
    }

    @Test
    fun messageCopied_postsShowMessageEvent() = runTest {
        val viewModel = createViewModel()

        viewModel.onAction(ChatAction.Ui.MessageCopied)

        viewModel.events.test {
            assertEquals(ChatEvent.ScrollToBottom, awaitItem())
            assertEquals(ChatEvent.ShowMessage("Скопировано"), awaitItem())
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun clearHistoryClicked_showsConfirmationDialog() = runTest {
        val viewModel = createViewModel()

        viewModel.onAction(ChatAction.Ui.ClearHistoryClicked)

        assertTrue(viewModel.uiState.value.showClearConfirmation)
    }

    @Test
    fun clearHistoryConfirmed_clearsMessagesAndPersistsThroughRepository() = runTest {
        val repository = FakeChatHistoryRepository()
        val stored = listOf(
            historyMessage(id = "1", text = "one"),
            historyMessage(id = "2", text = "two"),
        )
        val viewModel = createViewModel(storedMessages = stored, chatRepository = repository)

        viewModel.onAction(ChatAction.Ui.ClearHistoryClicked)
        viewModel.onAction(ChatAction.Ui.ClearHistoryConfirmed)

        assertTrue(viewModel.uiState.value.messages.isEmpty())
        assertTrue(repository.stored.isEmpty())
        assertFalse(viewModel.uiState.value.showClearConfirmation)
    }

    @Test
    fun clearHistoryCancelled_keepsHistoryIntactAndHidesDialog() = runTest {
        val repository = FakeChatHistoryRepository()
        val stored = listOf(
            historyMessage(id = "1", text = "one"),
            historyMessage(id = "2", text = "two"),
        )
        val viewModel = createViewModel(storedMessages = stored, chatRepository = repository)

        viewModel.onAction(ChatAction.Ui.ClearHistoryClicked)
        viewModel.onAction(ChatAction.Ui.ClearHistoryCancelled)

        assertEquals(listOf("1", "2"), viewModel.uiState.value.messages.map { message -> message.id })
        assertFalse(viewModel.uiState.value.showClearConfirmation)
        assertTrue(repository.stored.isNotEmpty())
    }

    @Test
    fun clearHistoryConfirmed_onRepositoryFailure_showsErrorAndKeepsHistoryIntact() = runTest {
        val repository = FakeChatHistoryRepository(clearError = IllegalStateException("disk error"))
        val stored = listOf(historyMessage(id = "1", text = "one"))
        val viewModel = createViewModel(storedMessages = stored, chatRepository = repository)

        viewModel.onAction(ChatAction.Ui.ClearHistoryClicked)
        viewModel.onAction(ChatAction.Ui.ClearHistoryConfirmed)

        assertEquals(listOf("1"), viewModel.uiState.value.messages.map { message -> message.id })
        viewModel.events.test {
            assertEquals(ChatEvent.ScrollToBottom, awaitItem())
            assertEquals(ChatEvent.ShowMessage("Failed to clear history. Please try again."), awaitItem())
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun deleteMessageClicked_showsConfirmationDialog() = runTest {
        val viewModel = createViewModel(
            storedMessages = listOf(historyMessage(id = "1", text = "one")),
        )

        viewModel.onAction(ChatAction.Ui.DeleteMessageClicked("1"))

        assertTrue(viewModel.uiState.value.isDeleteMessageConfirmationVisible)
    }

    @Test
    fun deleteMessageConfirmed_removesTargetMessageOnlyAndPersistsHistory() = runTest {
        val repository = FakeChatHistoryRepository()
        val stored = listOf(
            historyMessage(id = "1", text = "one"),
            historyMessage(id = "2", text = "two"),
        )
        val viewModel = createViewModel(storedMessages = stored, chatRepository = repository)

        viewModel.onAction(ChatAction.Ui.DeleteMessageClicked("1"))
        viewModel.onAction(ChatAction.Ui.DeleteMessageConfirmed)

        assertEquals(listOf("2"), viewModel.uiState.value.messages.map { message -> message.id })
        assertFalse(viewModel.uiState.value.isDeleteMessageConfirmationVisible)
        assertEquals(listOf("2"), repository.saved.last().map { message -> message.id })
    }

    @Test
    fun speakToggled_setsSpeakingFlagOnTargetMessageOnly() = runTest {
        val stored = listOf(
            historyMessage(id = "1", text = "one"),
            historyMessage(id = "2", text = "two"),
        )
        val viewModel = createViewModel(storedMessages = stored)

        viewModel.onAction(ChatAction.Ui.SpeakToggled("2"))

        val speaking = viewModel.uiState.value.messages.filter { message -> message.isSpeaking }
        assertEquals(listOf("2"), speaking.map { message -> message.id })
    }

    @Test
    fun speakToggled_calledTwiceForSameMessage_clearsSpeakingFlag() = runTest {
        val viewModel = createViewModel(storedMessages = listOf(historyMessage(id = "1", text = "one")))

        viewModel.onAction(ChatAction.Ui.SpeakToggled("1"))
        viewModel.onAction(ChatAction.Ui.SpeakToggled("1"))

        assertTrue(viewModel.uiState.value.messages.none { message -> message.isSpeaking })
    }

    @Test
    fun speakToggled_forDifferentMessage_switchesSpeakingMessage() = runTest {
        val stored = listOf(
            historyMessage(id = "1", text = "one"),
            historyMessage(id = "2", text = "two"),
        )
        val viewModel = createViewModel(storedMessages = stored)

        viewModel.onAction(ChatAction.Ui.SpeakToggled("1"))
        viewModel.onAction(ChatAction.Ui.SpeakToggled("2"))

        val speaking = viewModel.uiState.value.messages.filter { message -> message.isSpeaking }
        assertEquals(listOf("2"), speaking.map { message -> message.id })
    }

    @Test
    fun speechFinished_forActiveSpeakingMessage_clearsSpeakingFlag() = runTest {
        val viewModel = createViewModel(storedMessages = listOf(historyMessage(id = "1", text = "one")))
        viewModel.onAction(ChatAction.Ui.SpeakToggled("1"))

        viewModel.onAction(ChatAction.Ui.SpeechFinished("1"))

        assertTrue(viewModel.uiState.value.messages.none { message -> message.isSpeaking })
    }

    @Test
    fun speechFinished_forStaleMessageId_doesNotClearNewerSpeakingMessage() = runTest {
        val stored = listOf(
            historyMessage(id = "1", text = "one"),
            historyMessage(id = "2", text = "two"),
        )
        val viewModel = createViewModel(storedMessages = stored)
        viewModel.onAction(ChatAction.Ui.SpeakToggled("1"))
        viewModel.onAction(ChatAction.Ui.SpeakToggled("2"))

        viewModel.onAction(ChatAction.Ui.SpeechFinished("1"))

        val speaking = viewModel.uiState.value.messages.filter { message -> message.isSpeaking }
        assertEquals(listOf("2"), speaking.map { message -> message.id })
    }

    @Test
    fun deleteMessageCancelled_keepsAllMessagesAndHidesDialog() = runTest {
        val repository = FakeChatHistoryRepository()
        val stored = listOf(
            historyMessage(id = "1", text = "one"),
            historyMessage(id = "2", text = "two"),
        )
        val viewModel = createViewModel(storedMessages = stored, chatRepository = repository)

        viewModel.onAction(ChatAction.Ui.DeleteMessageClicked("1"))
        viewModel.onAction(ChatAction.Ui.DeleteMessageCancelled)

        assertEquals(listOf("1", "2"), viewModel.uiState.value.messages.map { message -> message.id })
        assertFalse(viewModel.uiState.value.isDeleteMessageConfirmationVisible)
        assertTrue(repository.saved.isEmpty())
    }

    private fun createViewModel(
        storedMessages: List<HistoryMessageModel> = emptyList(),
        chatRepository: FakeChatHistoryRepository = FakeChatHistoryRepository(),
        reply: String = "reply",
        aiError: Throwable? = null,
        aiRepository: AiRepository = FakeAiRepository(reply = reply, error = aiError),
    ): ChatViewModel {
        chatRepository.stored = storedMessages
        val sendMessageStreamUseCase = SendMessageStreamUseCase(repository = aiRepository)
        return ChatViewModel(
            sendMessageStreamUseCase = sendMessageStreamUseCase,
            loadChatHistoryUseCase = LoadChatHistoryUseCase(chatRepository),
            saveChatHistoryUseCase = SaveChatHistoryUseCase(chatRepository),
            clearChatHistoryUseCase = ClearChatHistoryUseCase(chatRepository),
            deleteMessageUseCase = DeleteMessageUseCase(chatRepository),
            exportChatHistoryUseCase = ExportChatHistoryUseCase(chatRepository),
            importChatHistoryUseCase = ImportChatHistoryUseCase(chatRepository),
            uiMapper = ChatUiMapper(),
        )
    }

    private fun historyMessage(id: String, text: String): HistoryMessageModel =
        HistoryMessageModel(
            id = id,
            author = MessageAuthor.USER,
            text = text,
            isFavorite = false,
            timestamp = TEST_TIMESTAMP,
        )

    private class FakeAiRepository(
        private val reply: String = "reply",
        private val error: Throwable? = null,
        private val chunks: List<String> = listOf(reply),
    ) : AiRepository {

        override suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel {
            error?.let { failure -> throw failure }
            return ChatMessageModel(author = MessageAuthor.ASSISTANT, text = reply)
        }

        override fun sendMessageStream(history: List<ChatMessageModel>): Flow<String> = flow {
            error?.let { failure -> throw failure }
            chunks.forEach { chunk -> emit(chunk) }
        }
    }

    private class SuspendingAiRepository : AiRepository {

        var wasCancelled: Boolean = false
            private set

        override suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel {
            try {
                awaitCancellation()
            } catch (cancellation: CancellationException) {
                wasCancelled = true
                throw cancellation
            }
        }

        override fun sendMessageStream(history: List<ChatMessageModel>): Flow<String> = flow {
            try {
                awaitCancellation()
            } catch (cancellation: CancellationException) {
                wasCancelled = true
                throw cancellation
            }
        }
    }

    private class PartialThenHangingAiRepository : AiRepository {

        var wasCancelled: Boolean = false
            private set

        override suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel =
            error("not used in streaming tests")

        override fun sendMessageStream(history: List<ChatMessageModel>): Flow<String> = flow {
            emit("Hel")
            emit("lo")
            try {
                awaitCancellation()
            } catch (cancellation: CancellationException) {
                wasCancelled = true
                throw cancellation
            }
        }
    }

    private class FailThenSucceedAiRepository(
        private val failure: Throwable,
        private val successReply: String,
    ) : AiRepository {

        private var callCount = 0

        override suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel =
            error("not used in streaming tests")

        override fun sendMessageStream(history: List<ChatMessageModel>): Flow<String> = flow {
            callCount += 1
            if (callCount == 1) {
                throw failure
            }
            emit(successReply)
        }
    }

    private class FakeChatHistoryRepository(
        private val importResult: List<HistoryMessageModel> = emptyList(),
        private val importError: Throwable? = null,
        private val exportResult: String = "/tmp/export.json",
        private val exportError: Throwable? = null,
        private val clearError: Throwable? = null,
    ) : ChatHistoryRepository {

        var stored: List<HistoryMessageModel> = emptyList()
        val saved: MutableList<List<HistoryMessageModel>> = mutableListOf()
        var lastImportStrategy: ImportStrategy? = null

        override suspend fun loadMessages(): List<HistoryMessageModel> = stored

        override suspend fun saveMessages(messages: List<HistoryMessageModel>) {
            saved += messages
            stored = messages
        }

        override suspend fun clearMessages() {
            clearError?.let { failure -> throw failure }
            stored = emptyList()
        }

        override suspend fun exportMessages(messages: List<HistoryMessageModel>): String {
            exportError?.let { failure -> throw failure }
            return exportResult
        }

        override suspend fun importMessages(
            json: String,
            strategy: ImportStrategy,
            current: List<HistoryMessageModel>,
        ): List<HistoryMessageModel> {
            importError?.let { failure -> throw failure }
            lastImportStrategy = strategy
            return importResult
        }
    }
}

private const val TEST_TIMESTAMP = 1_700_000_000_000L
