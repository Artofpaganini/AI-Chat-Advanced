package com.jarvis.chat.feature.ai.domain.model

data class MultiStageParseStepModel(
    val facts: MultiStageFactsModel,
    val meta: MultiStageStepMetaModel,
)
