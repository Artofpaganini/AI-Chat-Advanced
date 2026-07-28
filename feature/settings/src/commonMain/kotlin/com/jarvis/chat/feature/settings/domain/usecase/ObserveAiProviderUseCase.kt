package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.model.AiProviderModel
import com.jarvis.chat.feature.settings.domain.repository.AiProviderSettingsRepository
import kotlinx.coroutines.flow.StateFlow

class ObserveAiProviderUseCase internal constructor(
    private val repository: AiProviderSettingsRepository,
) {

    operator fun invoke(): StateFlow<AiProviderModel> = repository.observeAiProvider()
}
