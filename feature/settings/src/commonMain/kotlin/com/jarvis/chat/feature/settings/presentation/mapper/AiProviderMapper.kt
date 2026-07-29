package com.jarvis.chat.feature.settings.presentation.mapper

import com.jarvis.chat.feature.settings.domain.model.AiProviderModel
import com.jarvis.chat.feature.settings.presentation.model.AiProviderUiModel

internal fun AiProviderModel.toAiProviderUiModel(): AiProviderUiModel =
    when (this) {
        AiProviderModel.DEEP_SEEK_CLOUD -> AiProviderUiModel.DEEP_SEEK_CLOUD
        AiProviderModel.LOCAL_MLX -> AiProviderUiModel.LOCAL_MLX
        AiProviderModel.LOCAL_TRIAGE -> AiProviderUiModel.LOCAL_TRIAGE
    }

internal fun AiProviderUiModel.toAiProviderModel(): AiProviderModel =
    when (this) {
        AiProviderUiModel.DEEP_SEEK_CLOUD -> AiProviderModel.DEEP_SEEK_CLOUD
        AiProviderUiModel.LOCAL_MLX -> AiProviderModel.LOCAL_MLX
        AiProviderUiModel.LOCAL_TRIAGE -> AiProviderModel.LOCAL_TRIAGE
    }
