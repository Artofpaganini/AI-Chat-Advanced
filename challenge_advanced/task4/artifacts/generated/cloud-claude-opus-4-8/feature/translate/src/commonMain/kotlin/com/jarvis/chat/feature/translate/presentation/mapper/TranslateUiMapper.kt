package com.jarvis.chat.feature.translate.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

internal class TranslateUiMapper : UiMapper<TranslateState, TranslateUiModel> {

    override fun map(state: TranslateState): TranslateUiModel =
        TranslateUiModel(
            sourceText = state.sourceText,
            translatedText = state.translatedText,
            languages = TargetLanguage.entries,
            selectedLanguage = state.targetLanguage,
            isLoading = state.isLoading,
            isTranslateEnabled = state.sourceText.isNotBlank() && !state.isLoading,
            isErrorVisible = state.hasError,
            isResultVisible = state.translatedText.isNotBlank() && !state.isLoading,
        )
}
