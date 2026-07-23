package com.jarvis.chat.feature.translate.presentation

import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateEvent
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel

internal class TranslateViewModel(
    private val translateText: TranslateTextUseCase,
) : UdfBaseViewModel<TranslateAction, TranslateUiModel, TranslateState, TranslateEvent>(
    initialState = TranslateState(),
    uiMapper = TranslateUiMapper(),
) {
    override fun onAction(action: TranslateAction) {
        when (action) {
            is TranslateAction.Translate -> {
                updateState { copy(isLoading = true, error = null) }
                viewModelScope.launch {
                    try {
                        val result = translateText(action.text, action.targetLanguage)
                        updateState {
                            copy(
                                isLoading = false,
                                translation = result,
                            )
                        }
                    } catch (e: Exception) {
                        updateState {
                            copy(
                                isLoading = false,
                                error = e.message,
                            )
                        }
                        postEvent(TranslateEvent.ShowError(e.message ?: "Unknown error"))
                    }
                }
            }
            TranslateAction.Clear -> {
                updateState { copy(translation = null, error = null) }
            }
        }
    }
}
