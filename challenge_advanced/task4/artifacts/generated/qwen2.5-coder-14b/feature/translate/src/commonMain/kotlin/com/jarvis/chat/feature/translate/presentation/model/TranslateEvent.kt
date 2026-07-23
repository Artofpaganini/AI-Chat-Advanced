package com.jarvis.chat.feature.translate.presentation.model

sealed interface TranslateEvent {
    data class ShowError(val message: String) : TranslateEvent
}
