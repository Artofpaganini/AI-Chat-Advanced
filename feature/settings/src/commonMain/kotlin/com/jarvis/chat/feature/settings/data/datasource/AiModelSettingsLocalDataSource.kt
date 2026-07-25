package com.jarvis.chat.feature.settings.data.datasource

internal interface AiModelSettingsLocalDataSource {

    fun getAiModel(): String?

    fun saveAiModel(aiModel: String)
}
