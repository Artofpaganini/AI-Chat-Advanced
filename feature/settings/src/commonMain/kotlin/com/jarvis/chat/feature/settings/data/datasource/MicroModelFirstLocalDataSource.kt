package com.jarvis.chat.feature.settings.data.datasource

internal interface MicroModelFirstLocalDataSource {

    fun getMicroModelFirstEnabled(): Boolean?

    fun saveMicroModelFirstEnabled(enabled: Boolean)
}
