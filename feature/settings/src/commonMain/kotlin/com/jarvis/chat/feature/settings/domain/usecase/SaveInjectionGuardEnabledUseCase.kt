package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.repository.InjectionGuardSettingsRepository

internal class SaveInjectionGuardEnabledUseCase(
    private val repository: InjectionGuardSettingsRepository,
) {

    operator fun invoke(enabled: Boolean) {
        repository.saveInjectionGuardEnabled(enabled)
    }
}
