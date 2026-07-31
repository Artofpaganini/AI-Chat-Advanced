package com.jarvis.chat.feature.settings.domain.repository

import kotlinx.coroutines.flow.StateFlow

internal interface MicroModelFirstSettingsRepository {

    fun observeMicroModelFirstEnabled(): StateFlow<Boolean>

    fun saveMicroModelFirstEnabled(enabled: Boolean)
}
