package com.jarvis.chat.feature.settings.data.datasource

internal interface InferenceModeSettingsLocalDataSource {

    fun getInferenceMode(): String?

    fun saveInferenceMode(inferenceMode: String)
}
