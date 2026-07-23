package com.jarvis.chat.feature.translate.presentation.mapper

import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel
import com.jarvis.chat.core.viewmodel.UiMapper

internal class TranslateUiMapper : UiMapper<TranslateState, TranslateUiModel> {
    override fun map(state: TranslateState): TranslateUiModel =
        TranslateUiModel(
            translation = state.translation,
            isLoading = state.isLoading,
            error = state.error,
        )
}
