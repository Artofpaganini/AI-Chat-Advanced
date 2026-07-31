package com.jarvis.chat.feature.ai.domain.model

data class MultiStageAnswerStepModel(
    val answerText: String,
    val meta: MultiStageStepMetaModel,
)
