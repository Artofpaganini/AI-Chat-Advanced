package com.jarvis.chat.feature.settings.presentation.mapper

import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import com.jarvis.chat.feature.settings.presentation.model.AiModelUiModel

internal fun AiModelModel.toAiModelUiModel(): AiModelUiModel =
    when (this) {
        AiModelModel.FLASH -> AiModelUiModel.FLASH
        AiModelModel.PRO -> AiModelUiModel.PRO
    }

internal fun AiModelUiModel.toAiModelModel(): AiModelModel =
    when (this) {
        AiModelUiModel.FLASH -> AiModelModel.FLASH
        AiModelUiModel.PRO -> AiModelModel.PRO
    }
