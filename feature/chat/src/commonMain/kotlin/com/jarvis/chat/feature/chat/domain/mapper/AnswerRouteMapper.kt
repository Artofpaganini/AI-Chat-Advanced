package com.jarvis.chat.feature.chat.domain.mapper

import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel

private val EMERGENCY_ANSWER_MARKERS = listOf(
    "вызывайте скорую",
    "неотложная помощь",
    "экстренной помощи",
)
private val DOCTOR_SOON_ANSWER_MARKERS = listOf(
    "обратитесь к врачу в ближайшие дни",
    "покажите педиатру",
)
private val SELF_CARE_ANSWER_MARKERS = listOf(
    "наблюдайте дома",
    "можно справиться самим",
)

internal fun String.extractRouteFromAnswerText(): TriageRouteModel? {
    val normalized = normalizeForRouteExtraction()
    val matchedRoutes = buildSet {
        if (EMERGENCY_ANSWER_MARKERS.any { marker -> normalized.contains(marker) }) {
            add(TriageRouteModel.EMERGENCY)
        }
        if (DOCTOR_SOON_ANSWER_MARKERS.any { marker -> normalized.contains(marker) }) {
            add(TriageRouteModel.DOCTOR_SOON)
        }
        if (SELF_CARE_ANSWER_MARKERS.any { marker -> normalized.contains(marker) }) {
            add(TriageRouteModel.SELF_CARE)
        }
    }
    return matchedRoutes.singleOrNull()
}

private fun String.normalizeForRouteExtraction(): String = lowercase().replace("ё", "е")
