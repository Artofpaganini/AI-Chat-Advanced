package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.model.InferenceModeModel
import com.jarvis.chat.feature.settings.domain.repository.InferenceModeSettingsRepository
import kotlinx.coroutines.flow.StateFlow

class ObserveInferenceModeUseCase internal constructor(
    private val repository: InferenceModeSettingsRepository,
) {

    operator fun invoke(): StateFlow<InferenceModeModel> = repository.observeInferenceMode()
}
