package com.jarvis.chat.feature.settings.data.repository

import com.jarvis.chat.feature.settings.data.datasource.InjectionGuardLocalDataSource
import com.jarvis.chat.feature.settings.domain.repository.InjectionGuardSettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

private const val INJECTION_GUARD_DEFAULT_ENABLED = true

internal class InjectionGuardSettingsRepositoryImpl(
    private val localDataSource: InjectionGuardLocalDataSource,
) : InjectionGuardSettingsRepository {

    private val injectionGuardFlow: MutableStateFlow<Boolean> =
        MutableStateFlow(localDataSource.getInjectionGuardEnabled() ?: INJECTION_GUARD_DEFAULT_ENABLED)

    override fun observeInjectionGuardEnabled(): StateFlow<Boolean> = injectionGuardFlow.asStateFlow()

    override fun saveInjectionGuardEnabled(enabled: Boolean) {
        localDataSource.saveInjectionGuardEnabled(enabled)
        injectionGuardFlow.update { enabled }
    }
}
