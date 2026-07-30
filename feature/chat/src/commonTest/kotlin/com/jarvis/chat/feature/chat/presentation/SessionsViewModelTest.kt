package com.jarvis.chat.feature.chat.presentation

import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel
import com.jarvis.chat.feature.chat.domain.model.ChatSessionsModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository
import com.jarvis.chat.feature.chat.domain.usecase.CreateChatSessionUseCase
import com.jarvis.chat.feature.chat.domain.usecase.DeleteChatSessionUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatSessionsUseCase
import com.jarvis.chat.feature.chat.domain.usecase.RenameChatSessionUseCase
import com.jarvis.chat.feature.chat.domain.usecase.SwitchChatSessionUseCase
import com.jarvis.chat.feature.chat.presentation.mapper.SessionsUiMapper
import com.jarvis.chat.feature.chat.presentation.model.SessionsAction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
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

private const val TEST_TIMESTAMP = 1_700_000_000_000L

class SessionsViewModelTest {

    @BeforeTest
    fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
    }

    @AfterTest
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun init_loadsSessionsFromRepository() = runTest {
        val repository = FakeChatHistoryRepository(
            sessions = listOf(session(id = "s1"), session(id = "s2")),
            activeSessionId = "s1",
        )

        val viewModel = createViewModel(repository)

        assertEquals(listOf("s1", "s2"), viewModel.uiState.value.sessions.map { session -> session.id })
    }

    @Test
    fun openClicked_showsSheet() = runTest {
        val viewModel = createViewModel(FakeChatHistoryRepository())

        viewModel.onAction(SessionsAction.Ui.OpenClicked)

        assertTrue(viewModel.uiState.value.isSheetVisible)
    }

    @Test
    fun dismissRequested_hidesSheet() = runTest {
        val viewModel = createViewModel(FakeChatHistoryRepository())
        viewModel.onAction(SessionsAction.Ui.OpenClicked)

        viewModel.onAction(SessionsAction.Ui.DismissRequested)

        assertFalse(viewModel.uiState.value.isSheetVisible)
    }

    @Test
    fun createClicked_addsNewSessionToList() = runTest {
        val repository = FakeChatHistoryRepository(sessions = listOf(session(id = "s1")), activeSessionId = "s1")
        val viewModel = createViewModel(repository)

        viewModel.onAction(SessionsAction.Ui.CreateClicked)

        assertTrue(viewModel.uiState.value.sessions.any { session -> session.id == repository.createdSessionId })
    }

    @Test
    fun sessionClicked_switchesActiveSessionAndClosesSheet() = runTest {
        val repository = FakeChatHistoryRepository(sessions = listOf(session(id = "s1"), session(id = "s2")), activeSessionId = "s1")
        val viewModel = createViewModel(repository)
        viewModel.onAction(SessionsAction.Ui.OpenClicked)

        viewModel.onAction(SessionsAction.Ui.SessionClicked("s2"))

        assertEquals("s2", repository.lastSwitchedSessionId)
        assertFalse(viewModel.uiState.value.isSheetVisible)
    }

    @Test
    fun renameClicked_prefillsDialogWithCurrentTitle() = runTest {
        val repository = FakeChatHistoryRepository(sessions = listOf(session(id = "s1", title = "Old title")), activeSessionId = "s1")
        val viewModel = createViewModel(repository)

        viewModel.onAction(SessionsAction.Ui.RenameClicked("s1"))

        assertTrue(viewModel.uiState.value.isRenameDialogVisible)
        assertEquals("Old title", viewModel.uiState.value.renameTitle)
    }

    @Test
    fun renameConfirmed_persistsNewTitleAndHidesDialog() = runTest {
        val repository = FakeChatHistoryRepository(sessions = listOf(session(id = "s1", title = "Old title")), activeSessionId = "s1")
        val viewModel = createViewModel(repository)
        viewModel.onAction(SessionsAction.Ui.RenameClicked("s1"))
        viewModel.onAction(SessionsAction.Ui.RenameTitleChanged("New title"))

        viewModel.onAction(SessionsAction.Ui.RenameConfirmed)

        assertEquals("New title", repository.lastRenameTitle)
        assertFalse(viewModel.uiState.value.isRenameDialogVisible)
    }

    @Test
    fun deleteClicked_showsConfirmationDialog() = runTest {
        val viewModel = createViewModel(FakeChatHistoryRepository(sessions = listOf(session(id = "s1")), activeSessionId = "s1"))

        viewModel.onAction(SessionsAction.Ui.DeleteClicked("s1"))

        assertTrue(viewModel.uiState.value.isDeleteConfirmationVisible)
    }

    @Test
    fun deleteConfirmed_removesSessionAndUpdatesActive() = runTest {
        val repository = FakeChatHistoryRepository(
            sessions = listOf(session(id = "s1"), session(id = "s2")),
            activeSessionId = "s2",
            deleteResult = ChatSessionsModel(sessions = listOf(session(id = "s1")), activeSessionId = "s1"),
        )
        val viewModel = createViewModel(repository)

        viewModel.onAction(SessionsAction.Ui.DeleteClicked("s2"))
        viewModel.onAction(SessionsAction.Ui.DeleteConfirmed)

        assertEquals(listOf("s1"), viewModel.uiState.value.sessions.map { session -> session.id })
        assertFalse(viewModel.uiState.value.isDeleteConfirmationVisible)
    }

    @Test
    fun deleteCancelled_keepsSessionAndHidesDialog() = runTest {
        val repository = FakeChatHistoryRepository(sessions = listOf(session(id = "s1")), activeSessionId = "s1")
        val viewModel = createViewModel(repository)
        viewModel.onAction(SessionsAction.Ui.DeleteClicked("s1"))

        viewModel.onAction(SessionsAction.Ui.DeleteCancelled)

        assertFalse(viewModel.uiState.value.isDeleteConfirmationVisible)
        assertEquals(listOf("s1"), viewModel.uiState.value.sessions.map { session -> session.id })
    }

    private fun createViewModel(repository: FakeChatHistoryRepository): SessionsViewModel =
        SessionsViewModel(
            loadChatSessionsUseCase = LoadChatSessionsUseCase(repository),
            createChatSessionUseCase = CreateChatSessionUseCase(repository),
            switchChatSessionUseCase = SwitchChatSessionUseCase(repository),
            renameChatSessionUseCase = RenameChatSessionUseCase(repository),
            deleteChatSessionUseCase = DeleteChatSessionUseCase(repository),
            uiMapper = SessionsUiMapper(),
        )

    private fun session(id: String, title: String = "Chat $id"): ChatSessionModel =
        ChatSessionModel(id = id, title = title, createdAt = TEST_TIMESTAMP, lastMessageAt = TEST_TIMESTAMP, messageCount = 0)
}

private class FakeChatHistoryRepository(
    private var sessions: List<ChatSessionModel> = emptyList(),
    private var activeSessionId: String = "",
    private val deleteResult: ChatSessionsModel = ChatSessionsModel(sessions = emptyList(), activeSessionId = ""),
) : ChatHistoryRepository {

    var createdSessionId: String? = null
        private set
    var lastSwitchedSessionId: String? = null
        private set
    var lastRenameTitle: String? = null
        private set

    override fun observeActiveSessionId(): StateFlow<String?> = MutableStateFlow(activeSessionId)

    override suspend fun loadSessions(): ChatSessionsModel = ChatSessionsModel(sessions = sessions, activeSessionId = activeSessionId)

    override suspend fun createSession(): ChatSessionModel {
        val newSession = ChatSessionModel(id = "created-session", title = "", createdAt = 0L, lastMessageAt = 0L, messageCount = 0)
        createdSessionId = newSession.id
        sessions = sessions + newSession
        activeSessionId = newSession.id
        return newSession
    }

    override suspend fun renameSession(sessionId: String, title: String) {
        lastRenameTitle = title
        sessions = sessions.map { session -> if (session.id == sessionId) session.copy(title = title) else session }
    }

    override suspend fun deleteSession(sessionId: String): ChatSessionsModel {
        sessions = deleteResult.sessions
        activeSessionId = deleteResult.activeSessionId
        return deleteResult
    }

    override suspend fun switchSession(sessionId: String) {
        lastSwitchedSessionId = sessionId
        activeSessionId = sessionId
    }

    override suspend fun loadMessages(sessionId: String): List<HistoryMessageModel> = emptyList()

    override suspend fun saveMessages(sessionId: String, messages: List<HistoryMessageModel>) = Unit

    override suspend fun clearMessages(sessionId: String) = Unit

    override suspend fun exportMessages(messages: List<HistoryMessageModel>): String = ""

    override suspend fun importMessages(
        sessionId: String,
        json: String,
        strategy: ImportStrategy,
        current: List<HistoryMessageModel>,
    ): List<HistoryMessageModel> = emptyList()
}
