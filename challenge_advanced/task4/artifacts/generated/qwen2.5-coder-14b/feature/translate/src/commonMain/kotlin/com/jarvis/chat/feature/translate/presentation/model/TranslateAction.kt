package com.jarvis.chat.feature.translate.presentation.model

sealed interface TranslateAction {
    sealed interface Ui : TranslateAction {
        data class InputText(val text: String) : Ui
        data class SelectLanguage(val language: TargetLanguage) : Ui
        object Translate : Ui
    }

    sealed interface Internal : TranslateAction {
        data class TranslationResult(val translationModel: TranslationModel) : Internal
        data class Error(val message: String) : Internal
    }
}
