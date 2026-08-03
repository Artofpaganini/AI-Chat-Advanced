package com.jarvis.chat.feature.settings.data.datasource

internal interface InjectionGuardLocalDataSource {

    fun getInjectionGuardEnabled(): Boolean?

    fun saveInjectionGuardEnabled(enabled: Boolean)
}
