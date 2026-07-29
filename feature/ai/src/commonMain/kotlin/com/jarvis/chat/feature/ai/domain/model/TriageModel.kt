package com.jarvis.chat.feature.ai.domain.model

data class TriageModel(
    val route: TriageRouteModel,
    val routeLabel: String,
    val status: TriageStatusModel,
    val statusLabel: String,
    val confidence: Double,
    val explain: String,
    val crisis: Boolean,
)
