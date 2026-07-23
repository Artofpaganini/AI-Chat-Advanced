package com.jarvis.chat.feature.translate.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

internal class TranslateUiMapper : UiMapper<TranslateState, TranslateUiModel> {
    override fun map(state: TranslateState): TranslateUiModel =
        TranslateUiModel(
            sourceText = state.sourceText,
            targetLanguage = state.targetLanguage,
            translationModel = state.translationModel,
            errorMessage = state.errorMessage,
        )
}
