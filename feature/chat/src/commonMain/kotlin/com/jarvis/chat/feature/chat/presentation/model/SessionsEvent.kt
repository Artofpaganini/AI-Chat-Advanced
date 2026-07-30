package com.jarvis.chat.feature.chat.presentation.model

internal sealed interface SessionsEvent {

    data class ShowMessage(val text: String) : SessionsEvent
}
