package com.jarvis.chat.feature.settings.data.mapper

import com.jarvis.chat.feature.settings.domain.model.InferenceModeModel

private const val INFERENCE_MODE_ONE_SHOT = "ONE_SHOT"
private const val INFERENCE_MODE_MULTI_STAGE = "MULTI_STAGE"
private const val INFERENCE_MODE_CODE_LOOP = "CODE_LOOP"

internal fun InferenceModeModel.toStorageValue(): String =
    when (this) {
        InferenceModeModel.ONE_SHOT -> INFERENCE_MODE_ONE_SHOT
        InferenceModeModel.MULTI_STAGE -> INFERENCE_MODE_MULTI_STAGE
        InferenceModeModel.CODE_LOOP -> INFERENCE_MODE_CODE_LOOP
    }

internal fun String?.toInferenceModeModel(): InferenceModeModel =
    when (this) {
        INFERENCE_MODE_MULTI_STAGE -> InferenceModeModel.MULTI_STAGE
        INFERENCE_MODE_CODE_LOOP -> InferenceModeModel.CODE_LOOP
        else -> InferenceModeModel.ONE_SHOT
    }
