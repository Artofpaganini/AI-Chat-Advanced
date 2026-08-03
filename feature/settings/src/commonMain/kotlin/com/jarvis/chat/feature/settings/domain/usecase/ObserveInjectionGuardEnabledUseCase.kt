package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.repository.InjectionGuardSettingsRepository
import kotlinx.coroutines.flow.StateFlow

class ObserveInjectionGuardEnabledUseCase internal constructor(
    private val repository: InjectionGuardSettingsRepository,
) {

    operator fun invoke(): StateFlow<Boolean> = repository.observeInjectionGuardEnabled()
}
