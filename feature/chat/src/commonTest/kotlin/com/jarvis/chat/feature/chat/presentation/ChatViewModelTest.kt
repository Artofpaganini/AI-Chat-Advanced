package com.jarvis.chat.feature.chat.presentation

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageUseCase
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository
import com.jarvis.chat.feature.chat.domain.usecase.ClearChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ExportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ImportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.SaveChatHistoryUseCase
import com.jarvis.chat.feature.chat.presentation.mapper.ChatUiMapper
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.UnconfinedTestDispatcher
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
    fun voiceTranscribed_fillsInputLikeTyping() = runTest {
        val viewModel = createViewModel()

        viewModel.onAction(ChatAction.Ui.VoiceTranscribed("spoken text"))

        assertEquals("spoken text", viewModel.uiState.value.inputText)
    }

    private fun createViewModel(
        storedMessages: List<HistoryMessageModel> = emptyList(),
        chatRepository: FakeChatHistoryRepository = FakeChatHistoryRepository(),
        reply: String = "reply",
        aiError: Throwable? = null,
    ): ChatViewModel {
        chatRepository.stored = storedMessages
        val sendMessageUseCase = SendMessageUseCase(
            repository = FakeAiRepository(reply = reply, error = aiError),
        )
        return ChatViewModel(
            sendMessageUseCase = sendMessageUseCase,
            loadChatHistoryUseCase = LoadChatHistoryUseCase(chatRepository),
            saveChatHistoryUseCase = SaveChatHistoryUseCase(chatRepository),
            clearChatHistoryUseCase = ClearChatHistoryUseCase(chatRepository),
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
        private val reply: String,
        private val error: Throwable?,
    ) : AiRepository {

        override suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel {
            error?.let { failure -> throw failure }
            return ChatMessageModel(author = MessageAuthor.ASSISTANT, text = reply)
        }
    }

    private class FakeChatHistoryRepository(
        private val importResult: List<HistoryMessageModel> = emptyList(),
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
            stored = emptyList()
        }

        override suspend fun exportMessages(messages: List<HistoryMessageModel>): String = "/tmp/export.json"

        override suspend fun importMessages(
            json: String,
            strategy: ImportStrategy,
            current: List<HistoryMessageModel>,
        ): List<HistoryMessageModel> {
            lastImportStrategy = strategy
            return importResult
        }
    }
}

private const val TEST_TIMESTAMP = 1_700_000_000_000L
