package com.jarvis.chat.feature.settings.data.mapper

import com.jarvis.chat.feature.settings.domain.model.AiProviderModel

private const val AI_PROVIDER_DEEP_SEEK_CLOUD = "DEEP_SEEK_CLOUD"
private const val AI_PROVIDER_LOCAL_MLX = "LOCAL_MLX"

internal fun AiProviderModel.toStorageValue(): String =
    when (this) {
        AiProviderModel.DEEP_SEEK_CLOUD -> AI_PROVIDER_DEEP_SEEK_CLOUD
        AiProviderModel.LOCAL_MLX -> AI_PROVIDER_LOCAL_MLX
    }

internal fun String?.toAiProviderModel(): AiProviderModel =
    when (this) {
        AI_PROVIDER_LOCAL_MLX -> AiProviderModel.LOCAL_MLX
        else -> AiProviderModel.DEEP_SEEK_CLOUD
    }
