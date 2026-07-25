package com.jarvis.chat.feature.settings.presentation.model

import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel

internal sealed interface SettingsAction {

    sealed interface Ui : SettingsAction {

        data object OpenClicked : Ui

        data object DismissRequested : Ui

        data class ThemeModeSelected(val themeMode: ThemeModeUiModel) : Ui

        data class AiModelSelected(val aiModel: AiModelUiModel) : Ui
    }

    sealed interface Internal : SettingsAction {

        data class ThemeModeChanged(val themeMode: ThemeModeModel) : Internal

        data class AiModelChanged(val aiModel: AiModelModel) : Internal
    }
}
