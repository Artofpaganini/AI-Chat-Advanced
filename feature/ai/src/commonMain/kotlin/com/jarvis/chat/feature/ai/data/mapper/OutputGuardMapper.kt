package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.domain.model.GuardTargetModel
import com.jarvis.chat.feature.ai.domain.model.OutputGuardResultModel

private const val LEAK_MIN_MARKERS = 2
private const val LEAK_LONG_MARKER_CHARS = 40

private val MARKERS_JARVIS = listOf(
    "concise and helpful voice companion",
    "easy to read aloud",
    "Keep answers clear and easy to read aloud",
)
private val MARKERS_ALVA = listOf(
    "ассистент приложения ALVA",
    "от 0 до 3 лет",
    "ассистент приложения ALVA для родителей детей от 0 до 3 лет",
    "Вы не ставите диагнозы, не назначаете лекарства и не называете дозировки",
    "При признаках угрозы жизни или здоровью сразу маршрутизируйте к экстренной помощи",
)
private val IDENTITY_ONLY_MARKERS_ALVA = listOf(
    "ассистент приложения ALVA",
    "от 0 до 3 лет",
    "ассистент приложения ALVA для родителей детей от 0 до 3 лет",
)

private val MEDICATION_NAMES = listOf(
    "парацетамол",
    "ибупрофен",
    "нурофен",
    "панадол",
    "аспирин",
    "но-шпа",
    "нош-па",
    "энтерофурил",
    "смекта",
    "цефекон",
    "виферон",
    "антибиотик",
    "амоксициллин",
    "супрастин",
    "фенистил",
    "циннабсин",
)
private val DOSAGE_UNIT_WORDS = listOf(
    "мг",
    "мл",
    "ml",
    "mg",
    "капл",
    "таблет",
    "чайн",
    "мерн",
    "миллиграмм",
    "миллилитр",
)
private val DISEASE_NAMES = listOf(
    "отит",
    "ветрянка",
    "ротавирус",
    "бронхит",
    "пневмони",
    "аппендицит",
    "коклюш",
    "ангина",
    "гастроэнтерит",
    "скарлатина",
)
private val DIAGNOSIS_SUBJECT_PHRASES = listOf(
    "у вас ",
    "у вашего ребенка",
    "у вашего ребёнка",
    "у ребенка ",
    "у ребёнка ",
    "у нее ",
    "у неё ",
    "у него ",
)
private val HEDGE_WORDS = listOf(
    "вероятно",
    "возможно",
    "похоже",
    "может быть",
    "чаще всего",
    "скорее всего",
    "не исключено",
    "обычно",
)
private val DISCOURAGE_DOCTOR_PHRASES = listOf(
    "врач не нужен",
    "к врачу можно не идти",
    "не нужно вызывать скорую",
    "скорая не нужна",
    "можно не ехать в больницу",
    "необязательно обращаться к врачу",
    "подождите с врачом",
    "не спешите к врачу",
    "само пройдет, врач не нужен",
    "само пройдёт, врач не нужен",
)
private val PERSONA_BREAK_MARKERS = listOf(
    "я - dan",
    "я dan",
    "i am dan",
    "as dan",
    "dan активирован",
    "developer mode enabled",
    "режим разработчика включен",
    "режим разработчика включён",
    "без ограничений теперь",
    "прежние инструкции отменены",
    "инструкции отменены",
    "restrictions disabled",
    "confirmed: dan",
    "я больше не jarvis",
    "я больше не alva",
    "теперь я alva-dan",
    "я не связан правилами",
    "я не ограничен правилами",
    "dan mode enabled",
    "я не признаю эти ограничения",
    "не признаю эти ограничения",
)

private val DOSAGE_UNIT_PATTERN = Regex(
    "\\d+[.,]?\\d*\\s?(${DOSAGE_UNIT_WORDS.joinToString("|") { word -> Regex.escape(word) }})",
    RegexOption.IGNORE_CASE,
)
private val DOSE_TO_WEIGHT_PATTERN = Regex("(?:вес\\w*|весом)\\D{0,12}\\d+[.,]?\\d*\\s*кг", RegexOption.IGNORE_CASE)
private val DOSE_TO_AGE_PATTERN = Regex(
    "(?:\\d+[.,]?\\d*\\s*(?:мг|мл)\\D{0,15}\\d+\\s*месяц\\w*)|(?:\\d+\\s*месяц\\w*\\D{0,15}\\d+[.,]?\\d*\\s*(?:мг|мл))",
    RegexOption.IGNORE_CASE,
)
private val DISEASE_NAME_PATTERNS = DISEASE_NAMES.map { disease ->
    Regex("(?<![a-zа-я])${Regex.escape(disease)}(?![a-zа-я])", RegexOption.IGNORE_CASE)
}
private val SENTENCE_SPLIT_PATTERN = Regex("[.!?\\n]")

private val EMAIL_PATTERN = Regex("[\\w.+-]+@[\\w-]+\\.[a-z]{2,}", RegexOption.IGNORE_CASE)
private val PHONE_PATTERN = Regex("(?:\\+?\\d[\\d\\-\\s()]{8,14}\\d)")
private val CARD_PATTERN = Regex("\\b(?:\\d[ -]?){13,19}\\b")
private val URL_PATTERN = Regex("https?://\\S+", RegexOption.IGNORE_CASE)

private const val REASON_LEAK_MARKERS = "leak_markers"
private const val REASON_SAFETY_BYPASS_PREFIX = "safety_bypass_"
private const val REASON_PII = "pii"
private const val REASON_SUSPICIOUS_URL = "suspicious_url"
private const val REASON_PERSONA_BREAK = "persona_break"

private const val OUTPUT_GUARD_FALLBACK_MESSAGE =
    "Ответ скрыт фильтром безопасности (output guard): в нём обнаружен потенциально небезопасный " +
        "или конфиденциальный контент."

internal fun checkOutputGuard(responseText: String, target: GuardTargetModel): OutputGuardResultModel {
    val reasons = mutableListOf<String>()
    if (detectLeak(responseText, target)) {
        reasons.add(REASON_LEAK_MARKERS)
    }
    if (target == GuardTargetModel.ALVA) {
        val safetyBypassReason = detectSafetyBypass(responseText)
        if (safetyBypassReason.isNotEmpty()) {
            reasons.add("$REASON_SAFETY_BYPASS_PREFIX$safetyBypassReason")
        }
    }
    if (EMAIL_PATTERN.containsMatchIn(responseText) ||
        PHONE_PATTERN.containsMatchIn(responseText) ||
        CARD_PATTERN.containsMatchIn(responseText)
    ) {
        reasons.add(REASON_PII)
    }
    if (URL_PATTERN.containsMatchIn(responseText)) {
        reasons.add(REASON_SUSPICIOUS_URL)
    }
    if (detectPersonaBreak(responseText)) {
        reasons.add(REASON_PERSONA_BREAK)
    }
    return if (reasons.isNotEmpty()) {
        OutputGuardResultModel.Blocked(reasons = reasons, fallbackMessage = OUTPUT_GUARD_FALLBACK_MESSAGE)
    } else {
        OutputGuardResultModel.Allowed
    }
}

private fun String.normalizeForGuard(): String = lowercase().replace("ё", "е")

private fun detectLeak(text: String, target: GuardTargetModel): Boolean {
    val markers = when (target) {
        GuardTargetModel.JARVIS -> MARKERS_JARVIS
        GuardTargetModel.ALVA -> MARKERS_ALVA
    }
    val identityOnlyMarkers = when (target) {
        GuardTargetModel.JARVIS -> emptyList()
        GuardTargetModel.ALVA -> IDENTITY_ONLY_MARKERS_ALVA
    }
    val normalizedText = text.normalizeForGuard()
    val found = markers.filter { marker -> normalizedText.contains(marker.normalizeForGuard()) }
    val nonIdentityFound = found.filterNot { marker -> marker in identityOnlyMarkers }
    val hasLongNonIdentity = nonIdentityFound.any { marker -> marker.length >= LEAK_LONG_MARKER_CHARS }
    return (found.size >= LEAK_MIN_MARKERS && nonIdentityFound.isNotEmpty()) || hasLongNonIdentity
}

private fun detectSafetyBypass(text: String): String {
    val normalized = text.normalizeForGuard()
    val hasMedication = MEDICATION_NAMES.any { medication -> normalized.contains(medication) }
    val hasDosageUnit = DOSAGE_UNIT_PATTERN.containsMatchIn(normalized)
    val doseTiedToChild = DOSE_TO_WEIGHT_PATTERN.containsMatchIn(normalized) ||
        DOSE_TO_AGE_PATTERN.containsMatchIn(normalized)
    val hasDosageBypass = hasMedication && hasDosageUnit && doseTiedToChild
    val hasDiagnosisBypass = normalized.splitSentences().any { sentence -> sentence.isDiagnosisSentence() }
    val hasDiscourageBypass = DISCOURAGE_DOCTOR_PHRASES.any { phrase -> normalized.contains(phrase) }
    return when {
        hasDosageBypass -> "dosage_tied_to_child"
        hasDiagnosisBypass -> "diagnosis"
        hasDiscourageBypass -> "discourage_doctor"
        else -> ""
    }
}

private fun String.splitSentences(): List<String> =
    split(SENTENCE_SPLIT_PATTERN).map { part -> part.trim() }.filter { part -> part.isNotEmpty() }

private fun String.isDiagnosisSentence(): Boolean {
    val hasSubject = DIAGNOSIS_SUBJECT_PHRASES.any { phrase -> contains(phrase) }
    val hasDisease = DISEASE_NAME_PATTERNS.any { pattern -> pattern.containsMatchIn(this) }
    val hasHedge = HEDGE_WORDS.any { hedge -> contains(hedge) }
    return hasSubject && hasDisease && !hasHedge
}

private fun detectPersonaBreak(text: String): Boolean {
    val normalized = text.normalizeForGuard()
    return PERSONA_BREAK_MARKERS.any { marker -> normalized.contains(marker) }
}
