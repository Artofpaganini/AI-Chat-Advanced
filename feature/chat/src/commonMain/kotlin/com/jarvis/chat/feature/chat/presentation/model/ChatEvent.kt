package com.jarvis.chat.feature.chat.presentation.model

internal sealed interface ChatEvent {

    data object ScrollToBottom : ChatEvent

    data class ShowMessage(val text: String) : ChatEvent
}
