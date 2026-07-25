package com.jarvis.chat.feature.settings.data.mapper

import com.jarvis.chat.feature.settings.domain.model.AiModelModel

private const val AI_MODEL_FLASH = "FLASH"
private const val AI_MODEL_PRO = "PRO"

internal fun AiModelModel.toStorageValue(): String =
    when (this) {
        AiModelModel.FLASH -> AI_MODEL_FLASH
        AiModelModel.PRO -> AI_MODEL_PRO
    }

internal fun String?.toAiModelModel(): AiModelModel =
    when (this) {
        AI_MODEL_PRO -> AiModelModel.PRO
        else -> AiModelModel.FLASH
    }
