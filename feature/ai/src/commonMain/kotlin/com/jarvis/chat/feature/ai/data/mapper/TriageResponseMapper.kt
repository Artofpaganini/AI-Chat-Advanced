package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.TriageResponseModel
import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageStatusModel

internal fun TriageResponseModel.toTriageModel(): TriageModel =
    TriageModel(
        route = route.toTriageRouteModel(),
        routeLabel = routeLabel.orEmpty(),
        status = status.toTriageStatusModel(),
        statusLabel = statusLabel.orEmpty(),
        confidence = confidence ?: 0.0,
        explain = explain.orEmpty(),
        crisis = crisis ?: false,
    )

private fun String?.toTriageRouteModel(): TriageRouteModel =
    when (this) {
        "EMERGENCY" -> TriageRouteModel.EMERGENCY
        "DOCTOR_SOON" -> TriageRouteModel.DOCTOR_SOON
        "SELF_CARE" -> TriageRouteModel.SELF_CARE
        "OFF_TOPIC" -> TriageRouteModel.OFF_TOPIC
        "PARENT_SUPPORT" -> TriageRouteModel.PARENT_SUPPORT
        "DATA_INSIGHT" -> TriageRouteModel.DATA_INSIGHT
        else -> TriageRouteModel.UNKNOWN
    }

private fun String?.toTriageStatusModel(): TriageStatusModel =
    when (this) {
        "OK" -> TriageStatusModel.OK
        "UNSURE" -> TriageStatusModel.UNSURE
        "FAIL" -> TriageStatusModel.FAIL
        else -> TriageStatusModel.UNKNOWN
    }
