package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel
import com.jarvis.chat.feature.settings.domain.repository.ThemeSettingsRepository
import kotlinx.coroutines.flow.StateFlow

internal class ObserveThemeModeUseCase(
    private val repository: ThemeSettingsRepository,
) {

    operator fun invoke(): StateFlow<ThemeModeModel> = repository.observeThemeMode()
}
