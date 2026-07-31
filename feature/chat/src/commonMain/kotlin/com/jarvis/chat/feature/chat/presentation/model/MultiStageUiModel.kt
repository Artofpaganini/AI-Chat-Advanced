package com.jarvis.chat.feature.chat.presentation.model

internal data class MultiStageUiModel(
    val parseStep: MultiStageStepUiModel,
    val decideStep: MultiStageStepUiModel,
    val answerStep: MultiStageStepUiModel?,
    val summaryLabel: String,
)
