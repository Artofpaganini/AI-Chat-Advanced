package com.jarvis.chat.feature.chat.presentation.delegate

import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.usecase.ClearChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.DeleteMessageUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatSessionsUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ObserveActiveChatSessionUseCase
import com.jarvis.chat.feature.chat.domain.usecase.SaveChatHistoryUseCase
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import com.jarvis.chat.feature.chat.presentation.model.ChatEvent
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.launch

private const val CLEAR_HISTORY_MESSAGE = "Chat history cleared."
private const val CLEAR_HISTORY_FAILED_MESSAGE = "Failed to clear history. Please try again."
private const val DELETE_MESSAGE_MESSAGE = "Message deleted."
private const val DELETE_MESSAGE_FAILED_MESSAGE = "Failed to delete message. Please try again."

internal class ChatHistoryDelegate(
    private val loadChatSessionsUseCase: LoadChatSessionsUseCase,
    private val observeActiveChatSessionUseCase: ObserveActiveChatSessionUseCase,
    private val loadChatHistoryUseCase: LoadChatHistoryUseCase,
    private val saveChatHistoryUseCase: SaveChatHistoryUseCase,
    private val clearChatHistoryUseCase: ClearChatHistoryUseCase,
    private val deleteMessageUseCase: DeleteMessageUseCase,
    private val viewModelScope: CoroutineScope,
    private val currentState: () -> ChatState,
    private val updateState: (ChatState.() -> ChatState) -> Unit,
    private val postEvent: (ChatEvent) -> Unit,
    private val dispatch: (ChatAction) -> Unit,
    private val liveSessionMessages: (String) -> List<HistoryMessageModel>?,
    private val isSessionGenerating: (String) -> Boolean,
) {

    fun start() {
        viewModelScope.launch { loadChatSessionsUseCase() }
        viewModelScope.launch {
            observeActiveChatSessionUseCase().filterNotNull().collect { sessionId ->
                dispatch(ChatAction.Internal.ActiveSessionChanged(sessionId))
            }
        }
    }

    fun onActiveSessionChanged(sessionId: String) {
        val liveMessages = liveSessionMessages(sessionId)
        updateState {
            copy(
                activeSessionId = sessionId,
                messages = liveMessages ?: emptyList(),
                isLoading = isSessionGenerating(sessionId),
                error = null,
                pendingDeleteMessageId = null,
                showClearConfirmation = false,
            )
        }
        if (liveMessages != null) {
            postEvent(ChatEvent.ScrollToBottom)
            return
        }
        viewModelScope.launch {
            val messages = loadChatHistoryUseCase(sessionId)
            dispatch(ChatAction.Internal.HistoryLoaded(sessionId, messages))
        }
    }

    fun onHistoryLoaded(sessionId: String, messages: List<HistoryMessageModel>) {
        if (sessionId != currentState().activeSessionId) {
            return
        }
        updateState { copy(messages = messages) }
        postEvent(ChatEvent.ScrollToBottom)
    }

    fun persist(sessionId: String, messages: List<HistoryMessageModel>) {
        viewModelScope.launch {
            saveChatHistoryUseCase(sessionId, messages)
        }
    }

    fun onClearHistoryClicked() {
        updateState { copy(showClearConfirmation = true) }
    }

    fun onClearHistoryCancelled() {
        updateState { copy(showClearConfirmation = false) }
    }

    fun onClearHistoryConfirmed() {
        val sessionId = currentState().activeSessionId
        updateState { copy(showClearConfirmation = false) }
        viewModelScope.launch {
            clearChatHistoryUseCase(sessionId)
                .onSuccess { dispatch(ChatAction.Internal.HistoryCleared) }
                .onFailure { dispatch(ChatAction.Internal.ClearHistoryFailed) }
        }
    }

    fun onHistoryCleared() {
        updateState {
            copy(
                messages = emptyList(),
                isFavoritesFilterActive = false,
                error = null,
                lastSentText = "",
            )
        }
        postEvent(ChatEvent.ShowMessage(CLEAR_HISTORY_MESSAGE))
    }

    fun onClearHistoryFailed() {
        postEvent(ChatEvent.ShowMessage(CLEAR_HISTORY_FAILED_MESSAGE))
    }

    fun onDeleteMessageClicked(messageId: String) {
        updateState { copy(pendingDeleteMessageId = messageId) }
    }

    fun onDeleteMessageCancelled() {
        updateState { copy(pendingDeleteMessageId = null) }
    }

    fun onDeleteMessageConfirmed() {
        val messageId = currentState().pendingDeleteMessageId ?: return
        val sessionId = currentState().activeSessionId
        val messages = currentState().messages
        updateState { copy(pendingDeleteMessageId = null) }
        viewModelScope.launch {
            deleteMessageUseCase(sessionId = sessionId, messages = messages, messageId = messageId)
                .onSuccess { updatedMessages -> dispatch(ChatAction.Internal.MessageDeleted(updatedMessages)) }
                .onFailure { dispatch(ChatAction.Internal.DeleteMessageFailed) }
        }
    }

    fun onMessageDeleted(messages: List<HistoryMessageModel>) {
        updateState { copy(messages = messages) }
        postEvent(ChatEvent.ShowMessage(DELETE_MESSAGE_MESSAGE))
    }

    fun onDeleteMessageFailed() {
        postEvent(ChatEvent.ShowMessage(DELETE_MESSAGE_FAILED_MESSAGE))
    }
}
