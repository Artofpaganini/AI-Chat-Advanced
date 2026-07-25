package com.jarvis.chat.feature.settings.presentation.model

import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel

internal data class SettingsState(
    val themeMode: ThemeModeModel = ThemeModeModel.SYSTEM,
    val isSheetVisible: Boolean = false,
)
