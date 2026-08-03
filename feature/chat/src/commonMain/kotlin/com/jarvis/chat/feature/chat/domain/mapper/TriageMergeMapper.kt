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

private const val FALLBACK_LOW_CONFIDENCE_STATUS_LABEL = "Возможно экстренно (LLM не ответила)"
private const val FALLBACK_LOW_CONFIDENCE_EXPLAIN_TEXT =
    "Локальный классификатор заподозрил экстренную ситуацию, но не уверен, а подтверждения от большой модели нет."
private const val FALLBACK_LOW_CONFIDENCE_THRESHOLD = 0.65

private const val TEXT_ROUTE_STATUS_LABEL = "Оценка по тексту ответа"
private const val TEXT_ROUTE_EXPLAIN_TEXT =
    "Маршрут определён разбором текста ответа - отдельного поля с вердиктом сервер не прислал."
private const val TEXT_ROUTE_CONFIDENCE = 1.0

private const val TEXT_ROUTE_LABEL_EMERGENCY = "Экстренно"
private const val TEXT_ROUTE_LABEL_DOCTOR_SOON = "К врачу"
private const val TEXT_ROUTE_LABEL_SELF_CARE = "Можно дома"
private const val TEXT_ROUTE_LABEL_UNKNOWN = "Не определено"

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

internal fun MicroTriageModel.toFallbackTriageModel(): TriageModel {
    val isLowConfidence = confidence < FALLBACK_LOW_CONFIDENCE_THRESHOLD
    return TriageModel(
        route = route.toTriageRouteModel(),
        routeLabel = route.toRouteLabel(),
        status = TriageStatusModel.UNSURE,
        statusLabel = if (isLowConfidence) FALLBACK_LOW_CONFIDENCE_STATUS_LABEL else FALLBACK_STATUS_LABEL,
        confidence = confidence,
        explain = if (isLowConfidence) FALLBACK_LOW_CONFIDENCE_EXPLAIN_TEXT else FALLBACK_EXPLAIN_TEXT,
        crisis = true,
    )
}

internal fun TriageRouteModel.toTextEstimatedTriageModel(): TriageModel =
    TriageModel(
        route = this,
        routeLabel = toTextRouteLabel(),
        status = TriageStatusModel.UNSURE,
        statusLabel = TEXT_ROUTE_STATUS_LABEL,
        confidence = TEXT_ROUTE_CONFIDENCE,
        explain = TEXT_ROUTE_EXPLAIN_TEXT,
        crisis = this == TriageRouteModel.EMERGENCY,
    )

private fun TriageRouteModel.toTextRouteLabel(): String =
    when (this) {
        TriageRouteModel.EMERGENCY -> TEXT_ROUTE_LABEL_EMERGENCY
        TriageRouteModel.DOCTOR_SOON -> TEXT_ROUTE_LABEL_DOCTOR_SOON
        TriageRouteModel.SELF_CARE -> TEXT_ROUTE_LABEL_SELF_CARE
        TriageRouteModel.OFF_TOPIC,
        TriageRouteModel.PARENT_SUPPORT,
        TriageRouteModel.DATA_INSIGHT,
        TriageRouteModel.UNKNOWN,
        -> TEXT_ROUTE_LABEL_UNKNOWN
    }

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
