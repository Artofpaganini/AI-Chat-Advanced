package com.jarvis.chat.feature.settings.presentation.model

internal data class SettingsUiModel(
    val selectedThemeMode: ThemeModeUiModel,
    val selectedAiModel: AiModelUiModel,
    val selectedAiProvider: AiProviderUiModel,
    val isSheetVisible: Boolean,
)
