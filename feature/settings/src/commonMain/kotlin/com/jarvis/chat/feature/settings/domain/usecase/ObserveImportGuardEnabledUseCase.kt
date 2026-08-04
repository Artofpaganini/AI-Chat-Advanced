package com.jarvis.chat.feature.settings.domain.usecase

import com.jarvis.chat.feature.settings.domain.repository.ImportGuardSettingsRepository
import kotlinx.coroutines.flow.StateFlow

class ObserveImportGuardEnabledUseCase internal constructor(
    private val repository: ImportGuardSettingsRepository,
) {

    operator fun invoke(): StateFlow<Boolean> = repository.observeImportGuardEnabled()
}
