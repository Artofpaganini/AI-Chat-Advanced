package com.jarvis.chat.feature.chat.presentation

import androidx.lifecycle.viewModelScope
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageUseCase
import com.jarvis.chat.feature.chat.presentation.mapper.ChatUiMapper
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import com.jarvis.chat.feature.chat.presentation.model.ChatEvent
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import com.jarvis.chat.feature.chat.presentation.model.ChatUiModel
import kotlinx.coroutines.launch

internal class ChatViewModel(
    private val sendMessageUseCase: SendMessageUseCase,
    uiMapper: ChatUiMapper,
) : UdfBaseViewModel<ChatAction, ChatUiModel, ChatState, ChatEvent>(
    initialState = ChatState(),
    uiMapper = uiMapper,
) {

    override fun onAction(action: ChatAction) {
        when (action) {
            is ChatAction.Ui.InputChanged -> onInputChanged(action.text)
            is ChatAction.Ui.VoiceTranscribed -> onVoiceTranscribed(action.text)
            is ChatAction.Ui.SendClicked -> onSendClicked()
            is ChatAction.Internal.ReplyReceived -> onReplyReceived(action.message)
            is ChatAction.Internal.ReplyFailed -> onReplyFailed()
        }
    }

    private fun onInputChanged(text: String) {
        updateState { copy(inputText = text) }
    }

    private fun onVoiceTranscribed(text: String) {
        updateState { copy(inputText = text) }
    }

    private fun onSendClicked() {
        val text = currentState.inputText.trim()
        if (text.isEmpty() || currentState.isLoading) {
            return
        }
        val userMessage = ChatMessageModel(author = MessageAuthor.USER, text = text)
        val history = currentState.messages + userMessage
        updateState {
            copy(
                messages = history,
                inputText = "",
                isLoading = true,
                hasError = false,
            )
        }
        postEvent(ChatEvent.ScrollToBottom)
        requestReply(history)
    }

    private fun requestReply(history: List<ChatMessageModel>) {
        viewModelScope.launch {
            sendMessageUseCase(history)
                .onSuccess { reply -> onAction(ChatAction.Internal.ReplyReceived(reply)) }
                .onFailure { onAction(ChatAction.Internal.ReplyFailed) }
        }
    }

    private fun onReplyReceived(message: ChatMessageModel) {
        updateState {
            copy(
                messages = messages + message,
                isLoading = false,
                hasError = false,
            )
        }
        postEvent(ChatEvent.ScrollToBottom)
    }

    private fun onReplyFailed() {
        updateState {
            copy(
                isLoading = false,
                hasError = true,
            )
        }
    }
}
