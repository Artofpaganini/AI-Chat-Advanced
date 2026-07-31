package com.jarvis.chat.feature.chat.domain.model

import com.jarvis.chat.core.micromodel.domain.model.MicroTriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel

internal data class RouteDecisionModel(
    val source: RouteSourceModel,
    val microRoute: MicroTriageRouteModel,
    val microConfidence: Double,
    val elapsedMillis: Long,
    val llmRouteBeforeMerge: TriageRouteModel? = null,
)
