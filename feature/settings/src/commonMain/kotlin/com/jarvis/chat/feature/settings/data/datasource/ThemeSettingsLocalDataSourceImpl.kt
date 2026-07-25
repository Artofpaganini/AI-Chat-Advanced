package com.jarvis.chat.feature.settings.data.datasource

import com.russhwolf.settings.Settings

private const val KEY_THEME_MODE = "theme_mode"

internal class ThemeSettingsLocalDataSourceImpl(
    private val settings: Settings,
) : ThemeSettingsLocalDataSource {

    override fun getThemeMode(): String? = settings.getStringOrNull(KEY_THEME_MODE)

    override fun saveThemeMode(themeMode: String) {
        settings.putString(KEY_THEME_MODE, themeMode)
    }
}
