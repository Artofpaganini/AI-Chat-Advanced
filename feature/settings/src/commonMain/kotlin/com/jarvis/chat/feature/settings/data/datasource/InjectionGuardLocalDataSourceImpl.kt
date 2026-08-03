package com.jarvis.chat.feature.settings.data.datasource

import com.russhwolf.settings.Settings

private const val KEY_INJECTION_GUARD = "injection_guard_enabled"
private const val INJECTION_GUARD_DEFAULT_ENABLED = true

internal class InjectionGuardLocalDataSourceImpl(
    private val settings: Settings,
) : InjectionGuardLocalDataSource {

    override fun getInjectionGuardEnabled(): Boolean? =
        if (settings.hasKey(KEY_INJECTION_GUARD)) {
            settings.getBoolean(KEY_INJECTION_GUARD, INJECTION_GUARD_DEFAULT_ENABLED)
        } else {
            null
        }

    override fun saveInjectionGuardEnabled(enabled: Boolean) {
        settings.putBoolean(KEY_INJECTION_GUARD, enabled)
    }
}
