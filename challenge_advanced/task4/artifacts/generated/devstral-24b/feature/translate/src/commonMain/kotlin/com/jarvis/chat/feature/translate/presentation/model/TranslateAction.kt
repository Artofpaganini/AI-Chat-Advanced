package com.jarvis.chat.feature.translate.presentation.model

internal sealed interface TranslateAction {
    data class Ui(val action: UiAction) : TranslateAction
    data class Internal(val action: InternalAction) : TranslateAction

    sealed interface UiAction {
        data class OnTranslate(val sourceText: String, val targetLanguage: TargetLanguage) : UiAction
    }

    sealed interface InternalAction {
        object LoadTranslation : InternalAction
    }
}
