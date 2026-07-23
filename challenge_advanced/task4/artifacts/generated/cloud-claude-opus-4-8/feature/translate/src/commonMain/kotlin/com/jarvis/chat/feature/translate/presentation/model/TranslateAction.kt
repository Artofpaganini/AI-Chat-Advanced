package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal sealed interface TranslateAction {

    sealed interface Ui : TranslateAction {

        data class InputChanged(val text: String) : Ui

        data class LanguageSelected(val targetLanguage: TargetLanguage) : Ui

        data object TranslateClicked : Ui
    }

    sealed interface Internal : TranslateAction {

        data class TranslationReceived(val translation: TranslationModel) : Internal

        data object TranslationFailed : Internal
    }
}
