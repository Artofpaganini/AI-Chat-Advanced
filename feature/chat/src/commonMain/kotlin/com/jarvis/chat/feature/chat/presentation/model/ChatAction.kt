package com.jarvis.chat.feature.chat.presentation.model

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel

internal sealed interface ChatAction {

    sealed interface Ui : ChatAction {

        data class InputChanged(val text: String) : Ui

        data class VoiceTranscribed(val text: String) : Ui

        data object SendClicked : Ui
    }

    sealed interface Internal : ChatAction {

        data class ReplyReceived(val message: ChatMessageModel) : Internal

        data object ReplyFailed : Internal
    }
}
