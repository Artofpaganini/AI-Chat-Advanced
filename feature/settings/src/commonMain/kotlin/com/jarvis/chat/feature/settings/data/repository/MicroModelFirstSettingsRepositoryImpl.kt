package com.jarvis.chat.feature.settings.data.repository

import com.jarvis.chat.feature.settings.data.datasource.MicroModelFirstLocalDataSource
import com.jarvis.chat.feature.settings.domain.repository.MicroModelFirstSettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

private const val MICRO_MODEL_FIRST_DEFAULT_ENABLED = true

internal class MicroModelFirstSettingsRepositoryImpl(
    private val localDataSource: MicroModelFirstLocalDataSource,
) : MicroModelFirstSettingsRepository {

    private val microModelFirstFlow: MutableStateFlow<Boolean> =
        MutableStateFlow(localDataSource.getMicroModelFirstEnabled() ?: MICRO_MODEL_FIRST_DEFAULT_ENABLED)

    override fun observeMicroModelFirstEnabled(): StateFlow<Boolean> = microModelFirstFlow.asStateFlow()

    override fun saveMicroModelFirstEnabled(enabled: Boolean) {
        localDataSource.saveMicroModelFirstEnabled(enabled)
        microModelFirstFlow.update { enabled }
    }
}
