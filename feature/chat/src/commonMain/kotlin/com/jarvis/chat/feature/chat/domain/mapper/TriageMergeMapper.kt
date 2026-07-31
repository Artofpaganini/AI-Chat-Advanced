package com.jarvis.chat.feature.chat.domain.mapper

import com.jarvis.chat.core.micromodel.domain.model.MicroTriageModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageStatusModel

private const val SEVERITY_OFF_TOPIC = 0
private const val SEVERITY_SELF_CARE = 1
private const val SEVERITY_DOCTOR_SOON = 2
private const val SEVERITY_EMERGENCY = 3

private const val FALLBACK_STATUS_LABEL = "Экстренно (LLM не ответила)"
private const val FALLBACK_EXPLAIN_TEXT =
    "Большая модель не вернула собственную оценку. Показан результат локального классификатора."

internal fun TriageModel.mergeWithMicroRoute(microRoute: MicroTriageRouteModel?): TriageModel =
    if (microRoute == null) {
        this
    } else {
        val llmSeverity = route.toSeverityOrNull()
        val microSeverity = microRoute.toSeverity()
        val shouldOverrideWithMicro = microRoute == MicroTriageRouteModel.EMERGENCY ||
            (llmSeverity != null && llmSeverity < microSeverity)
        if (shouldOverrideWithMicro) {
            copy(route = microRoute.toTriageRouteModel(), routeLabel = microRoute.toRouteLabel())
        } else {
            this
        }
    }

internal fun TriageRouteModel?.mergeRouteWithMicroRoute(microRoute: MicroTriageRouteModel?): TriageRouteModel? =
    if (microRoute == null) {
        this
    } else {
        val llmSeverity = this?.toSeverityOrNull()
        val microSeverity = microRoute.toSeverity()
        val shouldOverrideWithMicro = microRoute == MicroTriageRouteModel.EMERGENCY ||
            (llmSeverity != null && llmSeverity < microSeverity)
        if (shouldOverrideWithMicro) microRoute.toTriageRouteModel() else this
    }

internal fun MicroTriageModel.toFallbackTriageModel(): TriageModel =
    TriageModel(
        route = route.toTriageRouteModel(),
        routeLabel = route.toRouteLabel(),
        status = TriageStatusModel.UNSURE,
        statusLabel = FALLBACK_STATUS_LABEL,
        confidence = confidence,
        explain = FALLBACK_EXPLAIN_TEXT,
        crisis = true,
    )

private fun MicroTriageRouteModel.toSeverity(): Int =
    when (this) {
        MicroTriageRouteModel.OFF_TOPIC -> SEVERITY_OFF_TOPIC
        MicroTriageRouteModel.SELF_CARE -> SEVERITY_SELF_CARE
        MicroTriageRouteModel.DOCTOR_SOON -> SEVERITY_DOCTOR_SOON
        MicroTriageRouteModel.EMERGENCY -> SEVERITY_EMERGENCY
    }

private fun TriageRouteModel.toSeverityOrNull(): Int? =
    when (this) {
        TriageRouteModel.OFF_TOPIC -> SEVERITY_OFF_TOPIC
        TriageRouteModel.SELF_CARE -> SEVERITY_SELF_CARE
        TriageRouteModel.DOCTOR_SOON -> SEVERITY_DOCTOR_SOON
        TriageRouteModel.EMERGENCY -> SEVERITY_EMERGENCY
        TriageRouteModel.PARENT_SUPPORT,
        TriageRouteModel.DATA_INSIGHT,
        TriageRouteModel.UNKNOWN,
        -> null
    }
