package com.jarvis.chat.feature.settings.domain.repository

import com.jarvis.chat.feature.settings.domain.model.AiProviderModel
import kotlinx.coroutines.flow.StateFlow

internal interface AiProviderSettingsRepository {

    fun observeAiProvider(): StateFlow<AiProviderModel>

    fun saveAiProvider(aiProvider: AiProviderModel)
}
