package com.jarvis.chat.feature.settings.data.datasource

import com.russhwolf.settings.Settings

private const val KEY_INFERENCE_MODE = "inference_mode"

internal class InferenceModeSettingsLocalDataSourceImpl(
    private val settings: Settings,
) : InferenceModeSettingsLocalDataSource {

    override fun getInferenceMode(): String? = settings.getStringOrNull(KEY_INFERENCE_MODE)

    override fun saveInferenceMode(inferenceMode: String) {
        settings.putString(KEY_INFERENCE_MODE, inferenceMode)
    }
}
