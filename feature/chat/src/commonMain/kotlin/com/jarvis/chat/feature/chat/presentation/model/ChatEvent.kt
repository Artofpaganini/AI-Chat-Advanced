package com.jarvis.chat.feature.chat.presentation.model

internal sealed interface ChatEvent {

    data object ScrollToBottom : ChatEvent
}
