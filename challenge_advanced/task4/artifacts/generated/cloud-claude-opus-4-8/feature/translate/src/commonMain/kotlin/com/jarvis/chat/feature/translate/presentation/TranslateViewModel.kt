package com.jarvis.chat.feature.translate.presentation

import androidx.lifecycle.viewModelScope
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.mapper.TranslateUiMapper
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateEvent
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel
import kotlinx.coroutines.launch

internal class TranslateViewModel(
    private val translateText: TranslateTextUseCase,
) : UdfBaseViewModel<TranslateAction, TranslateUiModel, TranslateState, TranslateEvent>(
    initialState = TranslateState(),
    uiMapper = TranslateUiMapper(),
) {

    override fun onAction(action: TranslateAction) {
        when (action) {
            is TranslateAction.Ui.InputChanged -> onInputChanged(action.text)
            is TranslateAction.Ui.LanguageSelected -> onLanguageSelected(action)
            is TranslateAction.Ui.TranslateClicked -> onTranslateClicked()
            is TranslateAction.Internal.TranslationReceived -> onTranslationReceived(action)
            is TranslateAction.Internal.TranslationFailed -> onTranslationFailed()
        }
    }

    private fun onInputChanged(text: String) {
        updateState { copy(sourceText = text, hasError = false) }
    }

    private fun onLanguageSelected(action: TranslateAction.Ui.LanguageSelected) {
        updateState { copy(targetLanguage = action.targetLanguage) }
    }

    private fun onTranslateClicked() {
        val state = currentState
        if (state.sourceText.isBlank() || state.isLoading) return
        updateState { copy(isLoading = true, hasError = false) }
        postEvent(TranslateEvent.HideKeyboard)
        viewModelScope.launch {
            runCatching { translateText(text = state.sourceText, targetLanguage = state.targetLanguage) }
                .onSuccess { translation -> onAction(TranslateAction.Internal.TranslationReceived(translation)) }
                .onFailure { error -> onAction(TranslateAction.Internal.TranslationFailed) }
        }
    }

    private fun onTranslationReceived(action: TranslateAction.Internal.TranslationReceived) {
        updateState {
            copy(
                translatedText = action.translation.translatedText,
                isLoading = false,
                hasError = false,
            )
        }
    }

    private fun onTranslationFailed() {
        updateState { copy(isLoading = false, hasError = true) }
        postEvent(TranslateEvent.ShowMessage("Не удалось перевести текст"))
    }
}
