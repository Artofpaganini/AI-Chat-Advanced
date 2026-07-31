package com.jarvis.chat.feature.ai.domain.repository

import com.jarvis.chat.feature.ai.domain.model.MultiStageResultModel

interface MultiStageAiRepository {

    suspend fun runMultiStage(caseText: String): MultiStageResultModel
}
