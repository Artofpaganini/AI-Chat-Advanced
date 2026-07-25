package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import com.jarvis.chat.feature.settings.domain.repository.AiModelSettingsRepository
import kotlinx.coroutines.flow.StateFlow

class ObserveAiModelUseCase internal constructor(
    private val repository: AiModelSettingsRepository,
) {

    operator fun invoke(): StateFlow<AiModelModel> = repository.observeAiModel()
}
