package com.jarvis.chat.feature.settings.data.repository

import com.jarvis.chat.feature.settings.data.datasource.AiProviderSettingsLocalDataSource
import com.jarvis.chat.feature.settings.data.mapper.toAiProviderModel
import com.jarvis.chat.feature.settings.data.mapper.toStorageValue
import com.jarvis.chat.feature.settings.domain.model.AiProviderModel
import com.jarvis.chat.feature.settings.domain.repository.AiProviderSettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

internal class AiProviderSettingsRepositoryImpl(
    private val localDataSource: AiProviderSettingsLocalDataSource,
) : AiProviderSettingsRepository {

    private val aiProviderFlow: MutableStateFlow<AiProviderModel> =
        MutableStateFlow(localDataSource.getAiProvider().toAiProviderModel())

    override fun observeAiProvider(): StateFlow<AiProviderModel> = aiProviderFlow.asStateFlow()

    override fun saveAiProvider(aiProvider: AiProviderModel) {
        localDataSource.saveAiProvider(aiProvider.toStorageValue())
        aiProviderFlow.update { aiProvider }
    }
}
