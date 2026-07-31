package com.jarvis.chat.feature.settings.presentation

import androidx.lifecycle.viewModelScope
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import com.jarvis.chat.feature.settings.domain.model.AiProviderModel
import com.jarvis.chat.feature.settings.domain.model.InferenceModeModel
import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel
import com.jarvis.chat.feature.settings.domain.usecase.ObserveAiModelUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveAiProviderUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveInferenceModeUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveMicroModelFirstEnabledUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveThemeModeUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveAiModelUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveAiProviderUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveInferenceModeUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveMicroModelFirstEnabledUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveThemeModeUseCase
import com.jarvis.chat.feature.settings.presentation.mapper.SettingsUiMapper
import com.jarvis.chat.feature.settings.presentation.mapper.toAiModelModel
import com.jarvis.chat.feature.settings.presentation.mapper.toAiProviderModel
import com.jarvis.chat.feature.settings.presentation.mapper.toInferenceModeModel
import com.jarvis.chat.feature.settings.presentation.mapper.toThemeModeModel
import com.jarvis.chat.feature.settings.presentation.model.AiModelUiModel
import com.jarvis.chat.feature.settings.presentation.model.AiProviderUiModel
import com.jarvis.chat.feature.settings.presentation.model.InferenceModeUiModel
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
    observeMicroModelFirstEnabledUseCase: ObserveMicroModelFirstEnabledUseCase,
    private val saveMicroModelFirstEnabledUseCase: SaveMicroModelFirstEnabledUseCase,
    observeInferenceModeUseCase: ObserveInferenceModeUseCase,
    private val saveInferenceModeUseCase: SaveInferenceModeUseCase,
    uiMapper: SettingsUiMapper,
) : UdfBaseViewModel<SettingsAction, SettingsUiModel, SettingsState, SettingsEvent>(
    initialState = SettingsState(
        themeMode = observeThemeModeUseCase().value,
        aiModel = observeAiModelUseCase().value,
        aiProvider = observeAiProviderUseCase().value,
        isMicroModelFirstEnabled = observeMicroModelFirstEnabledUseCase().value,
        inferenceMode = observeInferenceModeUseCase().value,
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
        viewModelScope.launch {
            observeMicroModelFirstEnabledUseCase().collect { enabled ->
                onAction(SettingsAction.Internal.MicroModelFirstChanged(enabled))
            }
        }
        viewModelScope.launch {
            observeInferenceModeUseCase().collect { inferenceMode ->
                onAction(SettingsAction.Internal.InferenceModeChanged(inferenceMode))
            }
        }
    }

    override fun onAction(action: SettingsAction) {
        when (action) {
            is SettingsAction.Ui.OpenClicked -> onOpenClicked()
            is SettingsAction.Ui.DismissRequested -> onDismissRequested()
            is SettingsAction.Ui.ThemeModeSelected -> onThemeModeSelected(action.themeMode)
            is SettingsAction.Ui.AiModelSelected -> onAiModelSelected(action.aiModel)
            is SettingsAction.Ui.AiProviderSelected -> onAiProviderSelected(action.aiProvider)
            is SettingsAction.Ui.MicroModelFirstToggled -> onMicroModelFirstToggled(action.enabled)
            is SettingsAction.Ui.InferenceModeSelected -> onInferenceModeSelected(action.inferenceMode)
            is SettingsAction.Internal.ThemeModeChanged -> onThemeModeChanged(action.themeMode)
            is SettingsAction.Internal.AiModelChanged -> onAiModelChanged(action.aiModel)
            is SettingsAction.Internal.AiProviderChanged -> onAiProviderChanged(action.aiProvider)
            is SettingsAction.Internal.MicroModelFirstChanged -> onMicroModelFirstChanged(action.enabled)
            is SettingsAction.Internal.InferenceModeChanged -> onInferenceModeChanged(action.inferenceMode)
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

    private fun onMicroModelFirstToggled(enabled: Boolean) {
        saveMicroModelFirstEnabledUseCase(enabled)
    }

    private fun onMicroModelFirstChanged(enabled: Boolean) {
        updateState { copy(isMicroModelFirstEnabled = enabled) }
    }

    private fun onInferenceModeSelected(inferenceMode: InferenceModeUiModel) {
        saveInferenceModeUseCase(inferenceMode.toInferenceModeModel())
        updateState { copy(isSheetVisible = false) }
    }

    private fun onInferenceModeChanged(inferenceMode: InferenceModeModel) {
        updateState { copy(inferenceMode = inferenceMode) }
    }
}
