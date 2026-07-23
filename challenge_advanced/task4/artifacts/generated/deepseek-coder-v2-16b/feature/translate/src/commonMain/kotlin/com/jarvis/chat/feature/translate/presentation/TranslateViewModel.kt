package com.jarvis.chat.feature.translate.presentation

import androidx.lifecycle.viewModelScope
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateEvent
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import kotlinx.coroutines.launch

internal class TranslateViewModel(
    private val translateText: TranslateTextUseCase,
) : UdfBaseViewModel<TranslateAction, TranslateUiModel, TranslateState, TranslateEvent>(
    initialState = TranslateState(),
    uiMapper = TranslateUiMapper()
) {
    override fun onAction(action: TranslateAction) {
        when (action) {
            is TranslateAction.Translate -> translate(action.text, action.targetLanguage)
        }
    }

    private fun translate(text: String, targetLanguage: String) {
        viewModelScope.launch {
            updateState { copy(isLoading = true) }
            try {
                val result = translateText(text, TargetLanguage.valueOf(targetLanguage)).first()
                postEvent(TranslateEvent.Translated(result.translatedText ?: ""))
            } catch (e: Exception) {
                updateState { copy(errorMessage = e.message ?: "Unknown error") }
            } finally {
                updateState { copy(isLoading = false) }
            }
        }
    }
}
