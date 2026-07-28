package com.jarvis.chat.feature.settings.data.datasource

import com.russhwolf.settings.Settings

private const val KEY_AI_PROVIDER = "ai_provider"

internal class AiProviderSettingsLocalDataSourceImpl(
    private val settings: Settings,
) : AiProviderSettingsLocalDataSource {

    override fun getAiProvider(): String? = settings.getStringOrNull(KEY_AI_PROVIDER)

    override fun saveAiProvider(aiProvider: String) {
        settings.putString(KEY_AI_PROVIDER, aiProvider)
    }
}
