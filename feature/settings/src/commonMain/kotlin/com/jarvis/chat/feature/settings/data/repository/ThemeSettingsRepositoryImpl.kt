package com.jarvis.chat.feature.settings.data.repository

import com.jarvis.chat.feature.settings.data.datasource.ThemeSettingsLocalDataSource
import com.jarvis.chat.feature.settings.data.mapper.toStorageValue
import com.jarvis.chat.feature.settings.data.mapper.toThemeModeModel
import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel
import com.jarvis.chat.feature.settings.domain.repository.ThemeSettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

internal class ThemeSettingsRepositoryImpl(
    private val localDataSource: ThemeSettingsLocalDataSource,
) : ThemeSettingsRepository {

    private val themeModeFlow: MutableStateFlow<ThemeModeModel> =
        MutableStateFlow(localDataSource.getThemeMode().toThemeModeModel())

    override fun observeThemeMode(): StateFlow<ThemeModeModel> = themeModeFlow.asStateFlow()

    override fun saveThemeMode(themeMode: ThemeModeModel) {
        localDataSource.saveThemeMode(themeMode.toStorageValue())
        themeModeFlow.update { themeMode }
    }
}
