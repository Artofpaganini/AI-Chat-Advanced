package com.jarvis.chat.feature.ai.domain.model

data class MultiStageResultModel(
    val parseStep: MultiStageParseStepModel,
    val decideStep: MultiStageDecideStepModel,
    val answerStep: MultiStageAnswerStepModel?,
    val route: TriageRouteModel?,
    val answerText: String,
    val failedStage: MultiStageStageModel?,
    val totalLatencyMs: Long,
    val totalCalls: Int,
    val totalCostUsd: Double?,
)
