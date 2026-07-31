package com.jarvis.chat.feature.settings.presentation.mapper

import com.jarvis.chat.feature.settings.domain.model.InferenceModeModel
import com.jarvis.chat.feature.settings.presentation.model.InferenceModeUiModel

internal fun InferenceModeModel.toInferenceModeUiModel(): InferenceModeUiModel =
    when (this) {
        InferenceModeModel.ONE_SHOT -> InferenceModeUiModel.ONE_SHOT
        InferenceModeModel.MULTI_STAGE -> InferenceModeUiModel.MULTI_STAGE
    }

internal fun InferenceModeUiModel.toInferenceModeModel(): InferenceModeModel =
    when (this) {
        InferenceModeUiModel.ONE_SHOT -> InferenceModeModel.ONE_SHOT
        InferenceModeUiModel.MULTI_STAGE -> InferenceModeModel.MULTI_STAGE
    }
