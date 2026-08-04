package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.repository.ImportGuardSettingsRepository

internal class SaveImportGuardEnabledUseCase(
    private val repository: ImportGuardSettingsRepository,
) {

    operator fun invoke(enabled: Boolean) {
        repository.saveImportGuardEnabled(enabled)
    }
}
