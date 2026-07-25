package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import com.jarvis.chat.feature.settings.domain.repository.AiModelSettingsRepository

internal class SaveAiModelUseCase(
    private val repository: AiModelSettingsRepository,
) {

    operator fun invoke(aiModel: AiModelModel) {
        repository.saveAiModel(aiModel)
    }
}
