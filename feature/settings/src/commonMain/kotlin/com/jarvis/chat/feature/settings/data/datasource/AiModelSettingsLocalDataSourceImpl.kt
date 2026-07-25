package com.jarvis.chat.feature.settings.data.datasource

import com.russhwolf.settings.Settings

private const val KEY_AI_MODEL = "ai_model"

internal class AiModelSettingsLocalDataSourceImpl(
    private val settings: Settings,
) : AiModelSettingsLocalDataSource {

    override fun getAiModel(): String? = settings.getStringOrNull(KEY_AI_MODEL)

    override fun saveAiModel(aiModel: String) {
        settings.putString(KEY_AI_MODEL, aiModel)
    }
}
