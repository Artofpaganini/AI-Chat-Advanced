package com.jarvis.chat.feature.chat.data.mapper

import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageStatusModel
import com.jarvis.chat.feature.chat.data.model.TriageDataModel

internal fun TriageDataModel.toTriageModel(): TriageModel =
    TriageModel(
        route = route.toTriageRouteModel(),
        routeLabel = routeLabel,
        status = status.toTriageStatusModel(),
        statusLabel = statusLabel,
        confidence = confidence,
        explain = explain,
        crisis = crisis,
    )

internal fun TriageModel.toTriageDataModel(): TriageDataModel =
    TriageDataModel(
        route = route.name,
        routeLabel = routeLabel,
        status = status.name,
        statusLabel = statusLabel,
        confidence = confidence,
        explain = explain,
        crisis = crisis,
    )

private fun String.toTriageRouteModel(): TriageRouteModel =
    TriageRouteModel.entries.find { route -> route.name == this } ?: TriageRouteModel.UNKNOWN

private fun String.toTriageStatusModel(): TriageStatusModel =
    TriageStatusModel.entries.find { status -> status.name == this } ?: TriageStatusModel.UNKNOWN
