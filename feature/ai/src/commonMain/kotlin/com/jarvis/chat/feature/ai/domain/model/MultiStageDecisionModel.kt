package com.jarvis.chat.feature.ai.domain.model

data class MultiStageDecisionModel(
    val route: TriageRouteModel?,
    val confidence: Double,
    val why: String,
)
