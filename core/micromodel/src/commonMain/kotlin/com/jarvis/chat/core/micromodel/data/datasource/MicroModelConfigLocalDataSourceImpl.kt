package com.jarvis.chat.core.micromodel.data.datasource

import com.jarvis.chat.core.micromodel.data.model.MicroModelConfigDataModel
import com.jarvis.chat.core.micromodel.resources.Res
import kotlinx.serialization.json.Json

private const val MICRO_MODEL_RESOURCE_PATH = "files/micro_model.json"

internal class MicroModelConfigLocalDataSourceImpl : MicroModelConfigLocalDataSource {

    private val json = Json { ignoreUnknownKeys = true }

    override suspend fun load(): MicroModelConfigDataModel {
        val bytes = Res.readBytes(MICRO_MODEL_RESOURCE_PATH)
        return json.decodeFromString(bytes.decodeToString())
    }
}
