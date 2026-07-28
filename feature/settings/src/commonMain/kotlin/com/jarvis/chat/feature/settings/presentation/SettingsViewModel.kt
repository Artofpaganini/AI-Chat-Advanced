package com.jarvis.chat.feature.settings.presentation

import androidx.lifecycle.viewModelScope
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import com.jarvis.chat.feature.settings.domain.model.AiProviderModel
import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel
import com.jarvis.chat.feature.settings.domain.usecase.ObserveAiModelUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveAiProviderUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveThemeModeUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveAiModelUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveAiProviderUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveThemeModeUseCase
import com.jarvis.chat.feature.settings.presentation.mapper.SettingsUiMapper
import com.jarvis.chat.feature.settings.presentation.mapper.toAiModelModel
import com.jarvis.chat.feature.settings.presentation.mapper.toAiProviderModel
import com.jarvis.chat.feature.settings.presentation.mapper.toThemeModeModel
import com.jarvis.chat.feature.settings.presentation.model.AiModelUiModel
import com.jarvis.chat.feature.settings.presentation.model.AiProviderUiModel
import com.jarvis.chat.feature.settings.presentation.model.SettingsAction
import com.jarvis.chat.feature.settings.presentation.model.SettingsEvent
import com.jarvis.chat.feature.settings.presentation.model.SettingsState
import com.jarvis.chat.feature.settings.presentation.model.SettingsUiModel
import com.jarvis.chat.feature.settings.presentation.model.ThemeModeUiModel
import kotlinx.coroutines.launch

internal class SettingsViewModel(
    observeThemeModeUseCase: ObserveThemeModeUseCase,
    private val saveThemeModeUseCase: SaveThemeModeUseCase,
    observeAiModelUseCase: ObserveAiModelUseCase,
    private val saveAiModelUseCase: SaveAiModelUseCase,
    observeAiProviderUseCase: ObserveAiProviderUseCase,
    private val saveAiProviderUseCase: SaveAiProviderUseCase,
    uiMapper: SettingsUiMapper,
) : UdfBaseViewModel<SettingsAction, SettingsUiModel, SettingsState, SettingsEvent>(
    initialState = SettingsState(
        themeMode = observeThemeModeUseCase().value,
        aiModel = observeAiModelUseCase().value,
        aiProvider = observeAiProviderUseCase().value,
    ),
    uiMapper = uiMapper,
) {

    init {
        viewModelScope.launch {
            observeThemeModeUseCase().collect { themeMode -> onAction(SettingsAction.Internal.ThemeModeChanged(themeMode)) }
        }
        viewModelScope.launch {
            observeAiModelUseCase().collect { aiModel -> onAction(SettingsAction.Internal.AiModelChanged(aiModel)) }
        }
        viewModelScope.launch {
            observeAiProviderUseCase().collect { aiProvider -> onAction(SettingsAction.Internal.AiProviderChanged(aiProvider)) }
        }
    }

    override fun onAction(action: SettingsAction) {
        when (action) {
            is SettingsAction.Ui.OpenClicked -> onOpenClicked()
            is SettingsAction.Ui.DismissRequested -> onDismissRequested()
            is SettingsAction.Ui.ThemeModeSelected -> onThemeModeSelected(action.themeMode)
            is SettingsAction.Ui.AiModelSelected -> onAiModelSelected(action.aiModel)
            is SettingsAction.Ui.AiProviderSelected -> onAiProviderSelected(action.aiProvider)
            is SettingsAction.Internal.ThemeModeChanged -> onThemeModeChanged(action.themeMode)
            is SettingsAction.Internal.AiModelChanged -> onAiModelChanged(action.aiModel)
            is SettingsAction.Internal.AiProviderChanged -> onAiProviderChanged(action.aiProvider)
        }
    }

    private fun onOpenClicked() {
        updateState { copy(isSheetVisible = true) }
    }

    private fun onDismissRequested() {
        updateState { copy(isSheetVisible = false) }
    }

    private fun onThemeModeSelected(themeMode: ThemeModeUiModel) {
        saveThemeModeUseCase(themeMode.toThemeModeModel())
        updateState { copy(isSheetVisible = false) }
    }

    private fun onThemeModeChanged(themeMode: ThemeModeModel) {
        updateState { copy(themeMode = themeMode) }
    }

    private fun onAiModelSelected(aiModel: AiModelUiModel) {
        saveAiModelUseCase(aiModel.toAiModelModel())
        updateState { copy(isSheetVisible = false) }
    }

    private fun onAiModelChanged(aiModel: AiModelModel) {
        updateState { copy(aiModel = aiModel) }
    }

    private fun onAiProviderSelected(aiProvider: AiProviderUiModel) {
        saveAiProviderUseCase(aiProvider.toAiProviderModel())
        updateState { copy(isSheetVisible = false) }
    }

    private fun onAiProviderChanged(aiProvider: AiProviderModel) {
        updateState { copy(aiProvider = aiProvider) }
    }
}
