package com.jarvis.chat.feature.settings.domain.repository

import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import kotlinx.coroutines.flow.StateFlow

internal interface AiModelSettingsRepository {

    fun observeAiModel(): StateFlow<AiModelModel>

    fun saveAiModel(aiModel: AiModelModel)
}
