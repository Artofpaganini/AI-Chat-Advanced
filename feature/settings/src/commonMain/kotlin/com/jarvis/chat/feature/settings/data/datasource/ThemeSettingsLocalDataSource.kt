package com.jarvis.chat.feature.settings.data.datasource

internal interface ThemeSettingsLocalDataSource {

    fun getThemeMode(): String?

    fun saveThemeMode(themeMode: String)
}
