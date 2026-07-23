package com.jarvis.chat.feature.translate.presentation

import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.mapper.TranslateUiMapper
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateEvent
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

internal class TranslateViewModel(
    private val translateTextUseCase: TranslateTextUseCase
) : UdfBaseViewModel<TranslateAction, TranslateUiModel, TranslateState, TranslateEvent>(
    initialState = TranslateState(),
    uiMapper = TranslateUiMapper()
) {

    override fun onAction(action: TranslateAction) {
        when (action) {
            is TranslateAction.Ui -> handleUiAction(action.action)
            is TranslateAction.Internal -> handleInternalAction(action.action)
        }
    }

    private fun handleUiAction(action: TranslateAction.UiAction) {
        when (action) {
            is TranslateAction.UiAction.OnTranslate -> {
                updateState { copy(sourceText = action.sourceText, targetLanguage = action.targetLanguage, isLoading = true, errorMessage = null) }
                onInternal(TranslateAction.Internal.LoadTranslation)
            }
        }
    }

    private fun handleInternalAction(action: TranslateAction.InternalAction) {
        when (action) {
            is TranslateAction.InternalAction.LoadTranslation -> {
                try {
                    val translation = translateTextUseCase(currentState.sourceText, currentState.targetLanguage!!)
                    updateState { copy(translatedText = translation.translatedText, isLoading = false) }
                } catch (e: Exception) {
                    postEvent(TranslateEvent.ShowError(e.message ?: "Unknown error"))
                    updateState { copy(isLoading = false, errorMessage = e.message) }
                }
            }
        }
    }
}
