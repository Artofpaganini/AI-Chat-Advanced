package com.jarvis.chat.feature.settings.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.settings.presentation.model.SettingsState
import com.jarvis.chat.feature.settings.presentation.model.SettingsUiModel

internal class SettingsUiMapper : UiMapper<SettingsState, SettingsUiModel> {

    override fun map(state: SettingsState): SettingsUiModel =
        SettingsUiModel(
            selectedThemeMode = state.themeMode.toThemeModeUiModel(),
            selectedAiModel = state.aiModel.toAiModelUiModel(),
            selectedAiProvider = state.aiProvider.toAiProviderUiModel(),
            isMicroModelFirstEnabled = state.isMicroModelFirstEnabled,
            selectedInferenceMode = state.inferenceMode.toInferenceModeUiModel(),
            isInjectionGuardEnabled = state.isInjectionGuardEnabled,
            isSheetVisible = state.isSheetVisible,
        )
}
