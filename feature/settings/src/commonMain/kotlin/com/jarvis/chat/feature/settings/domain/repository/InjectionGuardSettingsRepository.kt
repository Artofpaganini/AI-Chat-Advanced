package com.jarvis.chat.feature.settings.domain.repository

import kotlinx.coroutines.flow.StateFlow

internal interface InjectionGuardSettingsRepository {

    fun observeInjectionGuardEnabled(): StateFlow<Boolean>

    fun saveInjectionGuardEnabled(enabled: Boolean)
}
