package com.jarvis.chat.feature.chat.presentation.delegate

import com.jarvis.chat.feature.chat.presentation.model.ChatState

internal class ChatSpeechDelegate(
    private val currentState: () -> ChatState,
    private val updateState: (ChatState.() -> ChatState) -> Unit,
) {

    fun onSpeakToggled(messageId: String) {
        val nextSpeakingMessageId = if (currentState().speakingMessageId == messageId) null else messageId
        updateState { copy(speakingMessageId = nextSpeakingMessageId) }
    }

    fun onSpeechFinished(messageId: String) {
        if (currentState().speakingMessageId == messageId) {
            updateState { copy(speakingMessageId = null) }
        }
    }
}
