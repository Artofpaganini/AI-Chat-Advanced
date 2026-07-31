package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.repository.MicroModelFirstSettingsRepository

internal class SaveMicroModelFirstEnabledUseCase(
    private val repository: MicroModelFirstSettingsRepository,
) {

    operator fun invoke(enabled: Boolean) {
        repository.saveMicroModelFirstEnabled(enabled)
    }
}
