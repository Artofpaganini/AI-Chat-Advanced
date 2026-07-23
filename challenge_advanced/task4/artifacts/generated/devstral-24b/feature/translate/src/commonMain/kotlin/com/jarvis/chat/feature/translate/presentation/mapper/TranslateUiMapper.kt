package com.jarvis.chat.feature.translate.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

internal class TranslateUiMapper : UiMapper<TranslateState, TranslateUiModel> {
    override fun map(state: TranslateState): TranslateUiModel {
        return TranslateUiModel(
            sourceText = state.sourceText,
            targetLanguage = state.targetLanguage,
            translatedText = state.translatedText,
            isLoading = state.isLoading,
            errorMessage = state.errorMessage
        )
    }
}
