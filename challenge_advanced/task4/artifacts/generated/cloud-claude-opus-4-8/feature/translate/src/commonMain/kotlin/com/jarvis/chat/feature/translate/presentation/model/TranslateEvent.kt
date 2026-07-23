package com.jarvis.chat.feature.translate.presentation.model

internal sealed interface TranslateEvent {

    data object HideKeyboard : TranslateEvent

    data class ShowMessage(val text: String) : TranslateEvent
}
