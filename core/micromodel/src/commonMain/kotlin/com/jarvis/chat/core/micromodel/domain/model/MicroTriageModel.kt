package com.jarvis.chat.core.micromodel.domain.model

data class MicroTriageModel(
    val route: MicroTriageRouteModel,
    val status: MicroTriageStatusModel,
    val confidence: Double,
    val margin: Double,
    val probabilities: Map<MicroTriageRouteModel, Double>,
    val elapsedMillis: Long,
)
