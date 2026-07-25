package com.jarvis.chat.feature.settings.data.mapper

import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel

private const val THEME_MODE_SYSTEM = "SYSTEM"
private const val THEME_MODE_LIGHT = "LIGHT"
private const val THEME_MODE_DARK = "DARK"

internal fun ThemeModeModel.toStorageValue(): String =
    when (this) {
        ThemeModeModel.SYSTEM -> THEME_MODE_SYSTEM
        ThemeModeModel.LIGHT -> THEME_MODE_LIGHT
        ThemeModeModel.DARK -> THEME_MODE_DARK
    }

internal fun String?.toThemeModeModel(): ThemeModeModel =
    when (this) {
        THEME_MODE_LIGHT -> ThemeModeModel.LIGHT
        THEME_MODE_DARK -> ThemeModeModel.DARK
        else -> ThemeModeModel.SYSTEM
    }
