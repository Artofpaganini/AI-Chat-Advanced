package com.jarvis.chat.feature.ai.domain.model

data class MultiStageDecideStepModel(
    val decision: MultiStageDecisionModel,
    val meta: MultiStageStepMetaModel,
)
