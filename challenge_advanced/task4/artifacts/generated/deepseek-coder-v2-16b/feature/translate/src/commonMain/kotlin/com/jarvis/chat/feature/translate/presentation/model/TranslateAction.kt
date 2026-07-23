package com.jarvis.chat.feature.translate.presentation.model

internal sealed interface TranslateAction {
    data class Translate(val text: String, val targetLanguage: String) : TranslateAction
}
