package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.core.viewmodel.Action

internal sealed interface TranslateAction : Action {
    data class Translate(
        val text: String,
        val targetLanguage: String,
    ) : TranslateAction

    object Clear : TranslateAction
}
