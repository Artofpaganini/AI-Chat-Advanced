package com.jarvis.chat.feature.settings.domain.repository

import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel
import kotlinx.coroutines.flow.StateFlow

internal interface ThemeSettingsRepository {

    fun observeThemeMode(): StateFlow<ThemeModeModel>

    fun saveThemeMode(themeMode: ThemeModeModel)
}
