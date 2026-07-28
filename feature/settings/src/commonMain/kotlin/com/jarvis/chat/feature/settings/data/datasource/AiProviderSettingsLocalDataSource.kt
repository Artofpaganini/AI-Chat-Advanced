package com.jarvis.chat.feature.settings.data.datasource

internal interface AiProviderSettingsLocalDataSource {

    fun getAiProvider(): String?

    fun saveAiProvider(aiProvider: String)
}
