package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.model.InferenceModeModel
import com.jarvis.chat.feature.settings.domain.repository.InferenceModeSettingsRepository

internal class SaveInferenceModeUseCase(
    private val repository: InferenceModeSettingsRepository,
) {

    operator fun invoke(inferenceMode: InferenceModeModel) {
        repository.saveInferenceMode(inferenceMode)
    }
}
