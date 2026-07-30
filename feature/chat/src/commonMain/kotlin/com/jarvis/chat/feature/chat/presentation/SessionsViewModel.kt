package com.jarvis.chat.feature.chat.presentation

import androidx.lifecycle.viewModelScope
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel
import com.jarvis.chat.feature.chat.domain.usecase.CreateChatSessionUseCase
import com.jarvis.chat.feature.chat.domain.usecase.DeleteChatSessionUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatSessionsUseCase
import com.jarvis.chat.feature.chat.domain.usecase.RenameChatSessionUseCase
import com.jarvis.chat.feature.chat.domain.usecase.SwitchChatSessionUseCase
import com.jarvis.chat.feature.chat.presentation.mapper.SessionsUiMapper
import com.jarvis.chat.feature.chat.presentation.model.SessionsAction
import com.jarvis.chat.feature.chat.presentation.model.SessionsEvent
import com.jarvis.chat.feature.chat.presentation.model.SessionsState
import com.jarvis.chat.feature.chat.presentation.model.SessionsUiModel
import kotlinx.coroutines.launch

private const val OPERATION_FAILED_MESSAGE = "Something went wrong. Please try again."

internal class SessionsViewModel(
    private val loadChatSessionsUseCase: LoadChatSessionsUseCase,
    private val createChatSessionUseCase: CreateChatSessionUseCase,
    private val switchChatSessionUseCase: SwitchChatSessionUseCase,
    private val renameChatSessionUseCase: RenameChatSessionUseCase,
    private val deleteChatSessionUseCase: DeleteChatSessionUseCase,
    uiMapper: SessionsUiMapper,
) : UdfBaseViewModel<SessionsAction, SessionsUiModel, SessionsState, SessionsEvent>(
    initialState = SessionsState(),
    uiMapper = uiMapper,
) {

    init {
        loadSessions()
    }

    override fun onAction(action: SessionsAction) {
        when (action) {
            is SessionsAction.Ui.OpenClicked -> onOpenClicked()
            is SessionsAction.Ui.DismissRequested -> onDismissRequested()
            is SessionsAction.Ui.CreateClicked -> onCreateClicked()
            is SessionsAction.Ui.SessionClicked -> onSessionClicked(action.sessionId)
            is SessionsAction.Ui.RenameClicked -> onRenameClicked(action.sessionId)
            is SessionsAction.Ui.RenameTitleChanged -> onRenameTitleChanged(action.title)
            is SessionsAction.Ui.RenameConfirmed -> onRenameConfirmed()
            is SessionsAction.Ui.RenameCancelled -> onRenameCancelled()
            is SessionsAction.Ui.DeleteClicked -> onDeleteClicked(action.sessionId)
            is SessionsAction.Ui.DeleteConfirmed -> onDeleteConfirmed()
            is SessionsAction.Ui.DeleteCancelled -> onDeleteCancelled()
            is SessionsAction.Internal.SessionsLoaded -> onSessionsLoaded(action.sessions, action.activeSessionId)
            is SessionsAction.Internal.SessionCreated -> onSessionsLoaded(action.sessions, action.activeSessionId)
            is SessionsAction.Internal.SessionDeleted -> onSessionsLoaded(action.sessions, action.activeSessionId)
            is SessionsAction.Internal.OperationFailed -> onOperationFailed()
        }
    }

    private fun onOpenClicked() {
        updateState { copy(isSheetVisible = true) }
        loadSessions()
    }

    private fun onDismissRequested() {
        updateState { copy(isSheetVisible = false) }
    }

    private fun onCreateClicked() {
        viewModelScope.launch {
            createChatSessionUseCase()
                .onSuccess { loadSessions() }
                .onFailure { onAction(SessionsAction.Internal.OperationFailed) }
        }
    }

    private fun onSessionClicked(sessionId: String) {
        updateState { copy(isSheetVisible = false) }
        viewModelScope.launch {
            switchChatSessionUseCase(sessionId)
                .onFailure { onAction(SessionsAction.Internal.OperationFailed) }
        }
    }

    private fun onRenameClicked(sessionId: String) {
        val session = currentState.sessions.find { existingSession -> existingSession.id == sessionId } ?: return
        updateState { copy(pendingRenameSessionId = sessionId, pendingRenameTitle = session.title) }
    }

    private fun onRenameTitleChanged(title: String) {
        updateState { copy(pendingRenameTitle = title) }
    }

    private fun onRenameConfirmed() {
        val sessionId = currentState.pendingRenameSessionId ?: return
        val title = currentState.pendingRenameTitle.trim()
        updateState { copy(pendingRenameSessionId = null, pendingRenameTitle = "") }
        if (title.isEmpty()) {
            return
        }
        viewModelScope.launch {
            renameChatSessionUseCase(sessionId = sessionId, title = title)
                .onSuccess { loadSessions() }
                .onFailure { onAction(SessionsAction.Internal.OperationFailed) }
        }
    }

    private fun onRenameCancelled() {
        updateState { copy(pendingRenameSessionId = null, pendingRenameTitle = "") }
    }

    private fun onDeleteClicked(sessionId: String) {
        updateState { copy(pendingDeleteSessionId = sessionId) }
    }

    private fun onDeleteConfirmed() {
        val sessionId = currentState.pendingDeleteSessionId ?: return
        updateState { copy(pendingDeleteSessionId = null) }
        viewModelScope.launch {
            deleteChatSessionUseCase(sessionId)
                .onSuccess { sessions -> onAction(SessionsAction.Internal.SessionDeleted(sessions.sessions, sessions.activeSessionId)) }
                .onFailure { onAction(SessionsAction.Internal.OperationFailed) }
        }
    }

    private fun onDeleteCancelled() {
        updateState { copy(pendingDeleteSessionId = null) }
    }

    private fun onSessionsLoaded(sessions: List<ChatSessionModel>, activeSessionId: String) {
        updateState { copy(sessions = sessions, activeSessionId = activeSessionId) }
    }

    private fun onOperationFailed() {
        postEvent(SessionsEvent.ShowMessage(OPERATION_FAILED_MESSAGE))
    }

    private fun loadSessions() {
        viewModelScope.launch {
            val result = loadChatSessionsUseCase()
            onAction(SessionsAction.Internal.SessionsLoaded(result.sessions, result.activeSessionId))
        }
    }
}
