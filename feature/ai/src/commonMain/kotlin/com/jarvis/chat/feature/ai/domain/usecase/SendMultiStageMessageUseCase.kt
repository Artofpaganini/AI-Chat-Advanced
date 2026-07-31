package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.MultiStageResultModel
import com.jarvis.chat.feature.ai.domain.repository.MultiStageAiRepository

class SendMultiStageMessageUseCase(
    private val repository: MultiStageAiRepository,
) {

    suspend operator fun invoke(caseText: String): MultiStageResultModel = repository.runMultiStage(caseText)
}
