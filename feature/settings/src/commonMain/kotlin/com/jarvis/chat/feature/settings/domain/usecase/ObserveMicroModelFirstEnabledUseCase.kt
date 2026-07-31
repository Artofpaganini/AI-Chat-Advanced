package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.repository.MicroModelFirstSettingsRepository
import kotlinx.coroutines.flow.StateFlow

class ObserveMicroModelFirstEnabledUseCase internal constructor(
    private val repository: MicroModelFirstSettingsRepository,
) {

    operator fun invoke(): StateFlow<Boolean> = repository.observeMicroModelFirstEnabled()
}
