package com.jarvis.chat.feature.translate.presentation.model

internal sealed interface TranslateEvent {
    data class Translated(val translatedText: String) : TranslateEvent
}
