package com.jarvis.chat.feature.settings.data.repository

import com.jarvis.chat.feature.settings.data.datasource.ImportGuardLocalDataSource
import com.jarvis.chat.feature.settings.domain.repository.ImportGuardSettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

private const val IMPORT_GUARD_DEFAULT_ENABLED = true

internal class ImportGuardSettingsRepositoryImpl(
    private val localDataSource: ImportGuardLocalDataSource,
) : ImportGuardSettingsRepository {

    private val importGuardFlow: MutableStateFlow<Boolean> =
        MutableStateFlow(localDataSource.getImportGuardEnabled() ?: IMPORT_GUARD_DEFAULT_ENABLED)

    override fun observeImportGuardEnabled(): StateFlow<Boolean> = importGuardFlow.asStateFlow()

    override fun saveImportGuardEnabled(enabled: Boolean) {
        localDataSource.saveImportGuardEnabled(enabled)
        importGuardFlow.update { enabled }
    }
}
