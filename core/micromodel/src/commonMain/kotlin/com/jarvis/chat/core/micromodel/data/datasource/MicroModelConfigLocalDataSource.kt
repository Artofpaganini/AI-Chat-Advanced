package com.jarvis.chat.core.micromodel.data.datasource

import com.jarvis.chat.core.micromodel.data.model.MicroModelConfigDataModel

internal interface MicroModelConfigLocalDataSource {

    suspend fun load(): MicroModelConfigDataModel
}
