package com.jarvis.chat.feature.settings.data.datasource

import com.russhwolf.settings.Settings

private const val KEY_MICRO_MODEL_FIRST = "micro_model_first_enabled"
private const val MICRO_MODEL_FIRST_DEFAULT_ENABLED = true

internal class MicroModelFirstLocalDataSourceImpl(
    private val settings: Settings,
) : MicroModelFirstLocalDataSource {

    override fun getMicroModelFirstEnabled(): Boolean? =
        if (settings.hasKey(KEY_MICRO_MODEL_FIRST)) {
            settings.getBoolean(KEY_MICRO_MODEL_FIRST, MICRO_MODEL_FIRST_DEFAULT_ENABLED)
        } else {
            null
        }

    override fun saveMicroModelFirstEnabled(enabled: Boolean) {
        settings.putBoolean(KEY_MICRO_MODEL_FIRST, enabled)
    }
}
