package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.feature.chat.presentation.model.ChatState

private const val INPUT_GUARD_BADGE_TEXT = "Слой защиты L0: вход заблокирован фильтром нормализации"
private const val OUTPUT_GUARD_BADGE_PREFIX = "Слой защиты L3: ответ скрыт, причина - "
private const val OUTPUT_GUARD_REASON_SEPARATOR = ", "
private const val OUTPUT_GUARD_REASON_LEAK_MARKERS = "утечка системного промпта"
private const val OUTPUT_GUARD_REASON_SAFETY_BYPASS_DOSAGE = "дозировка, привязанная к ребёнку"
private const val OUTPUT_GUARD_REASON_SAFETY_BYPASS_DIAGNOSIS = "диагноз ребёнку"
private const val OUTPUT_GUARD_REASON_SAFETY_BYPASS_DISCOURAGE_DOCTOR = "отговор от обращения к врачу"
private const val OUTPUT_GUARD_REASON_SAFETY_BYPASS_OTHER = "обход правил детской безопасности"
private const val OUTPUT_GUARD_REASON_PII = "персональные данные"
private const val OUTPUT_GUARD_REASON_SUSPICIOUS_URL = "подозрительная ссылка"
private const val OUTPUT_GUARD_REASON_PERSONA_BREAK = "признаки смены личности"
private const val OUTPUT_GUARD_REASON_UNKNOWN = "неизвестная причина"

private const val INJECTION_GUARD_SUMMARY_PREFIX = "Защита от инъекций - отбито атак: "
private const val INJECTION_GUARD_SUMMARY_INPUT_PREFIX = " (вход: "
private const val INJECTION_GUARD_SUMMARY_OUTPUT_PREFIX = ", выход: "
private const val INJECTION_GUARD_SUMMARY_SUFFIX = ")"

internal fun inputGuardBadgeTextOrNull(isBlocked: Boolean): String? =
    if (isBlocked) INPUT_GUARD_BADGE_TEXT else null

internal fun List<String>.toOutputGuardBadgeTextOrNull(): String? {
    if (isEmpty()) {
        return null
    }
    val labels = map { reason -> reason.toOutputGuardReasonLabel() }
    return "$OUTPUT_GUARD_BADGE_PREFIX${labels.joinToString(OUTPUT_GUARD_REASON_SEPARATOR)}"
}

private fun String.toOutputGuardReasonLabel(): String =
    when {
        this == "leak_markers" -> OUTPUT_GUARD_REASON_LEAK_MARKERS
        this == "safety_bypass_dosage_tied_to_child" -> OUTPUT_GUARD_REASON_SAFETY_BYPASS_DOSAGE
        this == "safety_bypass_diagnosis" -> OUTPUT_GUARD_REASON_SAFETY_BYPASS_DIAGNOSIS
        this == "safety_bypass_discourage_doctor" -> OUTPUT_GUARD_REASON_SAFETY_BYPASS_DISCOURAGE_DOCTOR
        startsWith("safety_bypass_") -> OUTPUT_GUARD_REASON_SAFETY_BYPASS_OTHER
        this == "pii" -> OUTPUT_GUARD_REASON_PII
        this == "suspicious_url" -> OUTPUT_GUARD_REASON_SUSPICIOUS_URL
        this == "persona_break" -> OUTPUT_GUARD_REASON_PERSONA_BREAK
        else -> OUTPUT_GUARD_REASON_UNKNOWN
    }

internal fun ChatState.toInjectionGuardSessionSummaryOrNull(): String? {
    val blockedTotal = blockedInputCount + blockedOutputCount
    return if (blockedTotal > 0) {
        "$INJECTION_GUARD_SUMMARY_PREFIX$blockedTotal$INJECTION_GUARD_SUMMARY_INPUT_PREFIX$blockedInputCount" +
            "$INJECTION_GUARD_SUMMARY_OUTPUT_PREFIX$blockedOutputCount$INJECTION_GUARD_SUMMARY_SUFFIX"
    } else {
        null
    }
}
