package com.jarvis.chat.core.micromodel.domain.repository

import com.jarvis.chat.core.micromodel.domain.model.MicroTriageModel

internal interface MicroModelRepository {

    suspend fun classify(text: String): MicroTriageModel?
}
