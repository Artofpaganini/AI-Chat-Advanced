package com.jarvis.chat.feature.settings.presentation.model

import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import com.jarvis.chat.feature.settings.domain.model.AiProviderModel
import com.jarvis.chat.feature.settings.domain.model.InferenceModeModel
import com.jarvis.chat.feature.settings.domain.model.ThemeModeModel

internal data class SettingsState(
    val themeMode: ThemeModeModel = ThemeModeModel.SYSTEM,
    val aiModel: AiModelModel = AiModelModel.FLASH,
    val aiProvider: AiProviderModel = AiProviderModel.DEEP_SEEK_CLOUD,
    val isMicroModelFirstEnabled: Boolean = true,
    val inferenceMode: InferenceModeModel = InferenceModeModel.ONE_SHOT,
    val isInjectionGuardEnabled: Boolean = true,
    val isImportGuardEnabled: Boolean = true,
    val isSheetVisible: Boolean = false,
)
