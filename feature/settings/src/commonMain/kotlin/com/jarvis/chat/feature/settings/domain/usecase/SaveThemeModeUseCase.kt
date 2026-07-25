package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel
import com.jarvis.chat.feature.settings.domain.repository.ThemeSettingsRepository

internal class SaveThemeModeUseCase(
    private val repository: ThemeSettingsRepository,
) {

    operator fun invoke(themeMode: ThemeModeModel) {
        repository.saveThemeMode(themeMode)
    }
}
