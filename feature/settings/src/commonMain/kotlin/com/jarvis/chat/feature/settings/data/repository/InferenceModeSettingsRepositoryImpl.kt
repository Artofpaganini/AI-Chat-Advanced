package com.jarvis.chat.feature.settings.data.repository

import com.jarvis.chat.feature.settings.data.datasource.InferenceModeSettingsLocalDataSource
import com.jarvis.chat.feature.settings.data.mapper.toInferenceModeModel
import com.jarvis.chat.feature.settings.data.mapper.toStorageValue
import com.jarvis.chat.feature.settings.domain.model.InferenceModeModel
import com.jarvis.chat.feature.settings.domain.repository.InferenceModeSettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

internal class InferenceModeSettingsRepositoryImpl(
    private val localDataSource: InferenceModeSettingsLocalDataSource,
) : InferenceModeSettingsRepository {

    private val inferenceModeFlow: MutableStateFlow<InferenceModeModel> =
        MutableStateFlow(localDataSource.getInferenceMode().toInferenceModeModel())

    override fun observeInferenceMode(): StateFlow<InferenceModeModel> = inferenceModeFlow.asStateFlow()

    override fun saveInferenceMode(inferenceMode: InferenceModeModel) {
        localDataSource.saveInferenceMode(inferenceMode.toStorageValue())
        inferenceModeFlow.update { inferenceMode }
    }
}
