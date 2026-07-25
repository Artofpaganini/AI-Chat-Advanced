package com.jarvis.chat.feature.settings.presentation.mapper

import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel
import com.jarvis.chat.feature.settings.presentation.model.ThemeModeUiModel

internal fun ThemeModeModel.toThemeModeUiModel(): ThemeModeUiModel =
    when (this) {
        ThemeModeModel.SYSTEM -> ThemeModeUiModel.SYSTEM
        ThemeModeModel.LIGHT -> ThemeModeUiModel.LIGHT
        ThemeModeModel.DARK -> ThemeModeUiModel.DARK
    }

internal fun ThemeModeUiModel.toThemeModeModel(): ThemeModeModel =
    when (this) {
        ThemeModeUiModel.SYSTEM -> ThemeModeModel.SYSTEM
        ThemeModeUiModel.LIGHT -> ThemeModeModel.LIGHT
        ThemeModeUiModel.DARK -> ThemeModeModel.DARK
    }
