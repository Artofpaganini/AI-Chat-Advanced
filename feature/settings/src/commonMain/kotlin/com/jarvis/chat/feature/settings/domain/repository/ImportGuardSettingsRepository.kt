package com.jarvis.chat.feature.settings.domain.repository

import kotlinx.coroutines.flow.StateFlow

internal interface ImportGuardSettingsRepository {

    fun observeImportGuardEnabled(): StateFlow<Boolean>

    fun saveImportGuardEnabled(enabled: Boolean)
}
