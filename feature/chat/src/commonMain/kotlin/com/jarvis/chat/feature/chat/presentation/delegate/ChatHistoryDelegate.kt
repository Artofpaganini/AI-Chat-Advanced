package com.jarvis.chat.feature.chat.presentation.delegate

import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.usecase.ClearChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.DeleteMessageUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.SaveChatHistoryUseCase
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import com.jarvis.chat.feature.chat.presentation.model.ChatEvent
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

private const val CLEAR_HISTORY_MESSAGE = "Chat history cleared."
private const val CLEAR_HISTORY_FAILED_MESSAGE = "Failed to clear history. Please try again."
private const val DELETE_MESSAGE_MESSAGE = "Message deleted."
private const val DELETE_MESSAGE_FAILED_MESSAGE = "Failed to delete message. Please try again."

internal class ChatHistoryDelegate(
    private val loadChatHistoryUseCase: LoadChatHistoryUseCase,
    private val saveChatHistoryUseCase: SaveChatHistoryUseCase,
    private val clearChatHistoryUseCase: ClearChatHistoryUseCase,
    private val deleteMessageUseCase: DeleteMessageUseCase,
    private val viewModelScope: CoroutineScope,
    private val currentState: () -> ChatState,
    private val updateState: (ChatState.() -> ChatState) -> Unit,
    private val postEvent: (ChatEvent) -> Unit,
    private val dispatch: (ChatAction) -> Unit,
) {

    fun loadHistory() {
        viewModelScope.launch {
            val messages = loadChatHistoryUseCase()
            dispatch(ChatAction.Internal.HistoryLoaded(messages))
        }
    }

    fun onHistoryLoaded(messages: List<HistoryMessageModel>) {
        updateState { copy(messages = messages) }
        postEvent(ChatEvent.ScrollToBottom)
    }

    fun persist(messages: List<HistoryMessageModel>) {
        viewModelScope.launch {
            saveChatHistoryUseCase(messages)
        }
    }

    fun onClearHistoryClicked() {
        updateState { copy(showClearConfirmation = true) }
    }

    fun onClearHistoryCancelled() {
        updateState { copy(showClearConfirmation = false) }
    }

    fun onClearHistoryConfirmed() {
        updateState { copy(showClearConfirmation = false) }
        viewModelScope.launch {
            clearChatHistoryUseCase()
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
        val messages = currentState().messages
        updateState { copy(pendingDeleteMessageId = null) }
        viewModelScope.launch {
            deleteMessageUseCase(messages = messages, messageId = messageId)
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
