package com.jarvis.chat.feature.chat.domain.mapper

import com.jarvis.chat.core.micromodel.domain.model.MicroTriageModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageStatusModel

private const val LOCAL_STATUS_LABEL = "Локально"
private const val LOCAL_EXPLAIN_TEXT = "Определено локальной моделью без обращения к серверу"
private const val ROUTE_LABEL_EMERGENCY = "Экстренно"
private const val ROUTE_LABEL_DOCTOR_SOON = "К врачу"
private const val ROUTE_LABEL_SELF_CARE = "Можно дома"
private const val ROUTE_LABEL_OFF_TOPIC = "Не по теме"

private const val LOCAL_REPLY_SELF_CARE =
    "Похоже, это можно решить дома. Понаблюдайте за состоянием, и если станет хуже - обратитесь к врачу."
private const val LOCAL_REPLY_DOCTOR_SOON =
    "Рекомендуем в ближайшее время показаться врачу, чтобы уточнить состояние."
private const val LOCAL_REPLY_OFF_TOPIC =
    "Я помогаю с вопросами о здоровье и развитии ребёнка. Этот вопрос вне моей темы."
private const val LOCAL_REPLY_EMERGENCY =
    "Это сообщение требует внимания врача. Пожалуйста, обратитесь за помощью."

internal fun MicroTriageModel.toTriageModel(): TriageModel =
    TriageModel(
        route = route.toTriageRouteModel(),
        routeLabel = route.toRouteLabel(),
        status = TriageStatusModel.OK,
        statusLabel = LOCAL_STATUS_LABEL,
        confidence = confidence,
        explain = LOCAL_EXPLAIN_TEXT,
        crisis = false,
    )

internal fun MicroTriageRouteModel.toLocalReplyText(): String =
    when (this) {
        MicroTriageRouteModel.SELF_CARE -> LOCAL_REPLY_SELF_CARE
        MicroTriageRouteModel.DOCTOR_SOON -> LOCAL_REPLY_DOCTOR_SOON
        MicroTriageRouteModel.OFF_TOPIC -> LOCAL_REPLY_OFF_TOPIC
        MicroTriageRouteModel.EMERGENCY -> LOCAL_REPLY_EMERGENCY
    }

internal fun MicroTriageRouteModel.toTriageRouteModel(): TriageRouteModel =
    when (this) {
        MicroTriageRouteModel.EMERGENCY -> TriageRouteModel.EMERGENCY
        MicroTriageRouteModel.DOCTOR_SOON -> TriageRouteModel.DOCTOR_SOON
        MicroTriageRouteModel.SELF_CARE -> TriageRouteModel.SELF_CARE
        MicroTriageRouteModel.OFF_TOPIC -> TriageRouteModel.OFF_TOPIC
    }

internal fun MicroTriageRouteModel.toRouteLabel(): String =
    when (this) {
        MicroTriageRouteModel.EMERGENCY -> ROUTE_LABEL_EMERGENCY
        MicroTriageRouteModel.DOCTOR_SOON -> ROUTE_LABEL_DOCTOR_SOON
        MicroTriageRouteModel.SELF_CARE -> ROUTE_LABEL_SELF_CARE
        MicroTriageRouteModel.OFF_TOPIC -> ROUTE_LABEL_OFF_TOPIC
    }
