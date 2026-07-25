package com.jarvis.chat.feature.settings.data.repository

import com.jarvis.chat.feature.settings.data.datasource.AiModelSettingsLocalDataSource
import com.jarvis.chat.feature.settings.data.mapper.toAiModelModel
import com.jarvis.chat.feature.settings.data.mapper.toStorageValue
import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import com.jarvis.chat.feature.settings.domain.repository.AiModelSettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

internal class AiModelSettingsRepositoryImpl(
    private val localDataSource: AiModelSettingsLocalDataSource,
) : AiModelSettingsRepository {

    private val aiModelFlow: MutableStateFlow<AiModelModel> =
        MutableStateFlow(localDataSource.getAiModel().toAiModelModel())

    override fun observeAiModel(): StateFlow<AiModelModel> = aiModelFlow.asStateFlow()

    override fun saveAiModel(aiModel: AiModelModel) {
        localDataSource.saveAiModel(aiModel.toStorageValue())
        aiModelFlow.update { aiModel }
    }
}
