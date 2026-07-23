package com.jarvis.chat.feature.translate.presentation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
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
    uiMapper = TranslateUiMapper(),
) {

    override fun onAction(action: TranslateAction) {
        when (action) {
            is TranslateAction.Ui.InputText -> updateState { copy(sourceText = action.text) }
            is TranslateAction.Ui.SelectLanguage -> updateState { copy(targetLanguage = action.language) }
            TranslateAction.Ui.Translate -> translate()
            is TranslateAction.Internal.TranslationResult -> updateState { copy(translationModel = action.translationModel, errorMessage = null) }
            is TranslateAction.Internal.Error -> postEvent(TranslateEvent.ShowError(action.message))
        }
    }

    private fun translate() {
        val sourceText = currentState.sourceText
        val targetLanguage = currentState.targetLanguage

        if (sourceText.isNotEmpty()) {
            viewModelScope.launch {
                try {
                    val translationModel = translateText.execute(sourceText, targetLanguage)
                    updateState { copy(translationModel = translationModel) }
                } catch (e: Exception) {
                    postEvent(TranslateEvent.ShowError(e.message ?: "An error occurred"))
                }
            }
        }
    }
}
