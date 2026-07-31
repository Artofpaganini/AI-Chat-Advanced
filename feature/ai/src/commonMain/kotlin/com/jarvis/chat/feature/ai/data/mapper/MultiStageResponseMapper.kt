package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.di.MultiStageDefaults
import com.jarvis.chat.feature.ai.domain.model.MultiStageDecisionModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageFactsModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageQuestionTypeModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageViolationModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel
import kotlin.math.round

private const val VALUE_TAIL_CHARS = " \t\r\n|,.;*`\"'"
private const val CONFIDENCE_ROUND_SCALE = 10_000.0

private val NONE_ALIASES = setOf(
    "none",
    "нет",
    "-",
    "--",
    "null",
    "n/a",
    "не указано",
    "не указан",
    "не указана",
    "неизвестно",
    "отсутствует",
)

private val STAGE1_REQUIRED_FIELDS = listOf(
    MultiStageDefaults.F_AGE,
    MultiStageDefaults.F_SYMPTOMS,
    MultiStageDefaults.F_METRICS,
    MultiStageDefaults.F_DURATION,
    MultiStageDefaults.F_PARENT_STATE,
    MultiStageDefaults.F_QUESTION_TYPE,
)

private val CODE_FENCE_PATTERN = Regex(
    "^\\s*```[a-zA-Z0-9_+-]*[ \\t]*\\r?\\n?(.*?)\\r?\\n?\\s*```\\s*\$",
    RegexOption.DOT_MATCHES_ALL,
)

private val STAGE1_KEY_PATTERN = Regex(
    "(?<![A-Za-z_])(QUESTION_TYPE|PARENT_STATE|AGE_MONTHS|SYMPTOMS|DURATION|METRICS)\\s*[=:]",
    RegexOption.IGNORE_CASE,
)

private val STAGE2_KEY_PATTERN = Regex(
    "(?<![A-Za-z_])(ROUTE|CONFIDENCE|WHY)\\s*[=:]",
    RegexOption.IGNORE_CASE,
)

private val LEAK_PATTERN = Regex(
    "(?<![A-Za-z_])(EMERGENCY|DOCTOR_SOON|SELF_CARE|OFF_TOPIC|PARENT_SUPPORT|DATA_INSIGHT)(?![A-Za-z_])",
    RegexOption.IGNORE_CASE,
)

private val INTEGER_PATTERN = Regex("-?\\d+")
private val NUMBER_PATTERN = Regex("-?\\d+(?:[.,]\\d+)?")
private val WORD_PATTERN = Regex("[A-Za-z_]+")

internal data class MultiStageParseOutcome(
    val facts: MultiStageFactsModel,
    val violations: List<MultiStageViolationModel>,
)

internal data class MultiStageDecideOutcome(
    val decision: MultiStageDecisionModel,
    val violations: List<MultiStageViolationModel>,
)

internal fun parseStage1Facts(raw: String): MultiStageParseOutcome {
    val violations = mutableListOf<MultiStageViolationModel>()
    val text = stripCodeFence(raw)
    if (routeLeaked(raw)) {
        violations.add(MultiStageViolationModel.S1_ROUTE_LEAKED)
    }
    val pairs = collectPairs(text, STAGE1_KEY_PATTERN)
    if (pairs.isEmpty()) {
        violations.add(MultiStageViolationModel.S1_PARSE)
        return MultiStageParseOutcome(facts = emptyMultiStageFacts(), violations = violations)
    }
    val broken = STAGE1_REQUIRED_FIELDS.filter { name -> name !in pairs }
    val (age, ageOutOfRange) = parseAge(pairs[MultiStageDefaults.F_AGE])
    val (questionType, questionTypeBroken) = parseQuestionType(pairs[MultiStageDefaults.F_QUESTION_TYPE])
    val facts = MultiStageFactsModel(
        ageMonths = age,
        symptoms = parseSymptoms(pairs[MultiStageDefaults.F_SYMPTOMS]),
        metrics = parseFreeField(pairs[MultiStageDefaults.F_METRICS], MultiStageDefaults.MAX_METRICS_CHARS),
        duration = parseFreeField(pairs[MultiStageDefaults.F_DURATION], MultiStageDefaults.MAX_DURATION_CHARS),
        parentState = parseFreeField(
            pairs[MultiStageDefaults.F_PARENT_STATE],
            MultiStageDefaults.MAX_PARENT_STATE_CHARS,
        ),
        questionType = questionType,
    )
    if (broken.isNotEmpty() || ageOutOfRange || questionTypeBroken) {
        violations.add(MultiStageViolationModel.S1_PARSE)
    }
    return MultiStageParseOutcome(facts = facts, violations = violations)
}

internal fun parseStage2Decision(raw: String): MultiStageDecideOutcome {
    val violations = mutableListOf<MultiStageViolationModel>()
    val text = stripCodeFence(raw)
    val pairs = collectPairs(text, STAGE2_KEY_PATTERN)
    var route = parseRouteValue(pairs[MultiStageDefaults.D_ROUTE])
    if (route == null) {
        route = parseRouteValue(text)
        if (route != null) {
            violations.add(MultiStageViolationModel.S2_PARSE)
        }
    }
    val (confidence, confidenceBroken) = parseConfidence(pairs[MultiStageDefaults.D_CONFIDENCE])
    var why = parseFreeField(pairs[MultiStageDefaults.D_WHY], MultiStageDefaults.MAX_WHY_CHARS)
    if (why == MultiStageDefaults.NONE_VALUE) {
        why = ""
    }
    val roundedConfidence = round(confidence * CONFIDENCE_ROUND_SCALE) / CONFIDENCE_ROUND_SCALE
    val decision = MultiStageDecisionModel(route = route, confidence = roundedConfidence, why = why)
    if (route == null || confidenceBroken || MultiStageDefaults.D_WHY !in pairs) {
        if (MultiStageViolationModel.S2_PARSE !in violations) {
            violations.add(MultiStageViolationModel.S2_PARSE)
        }
    }
    return MultiStageDecideOutcome(decision = decision, violations = violations)
}

internal fun MultiStageFactsModel.toFormattedFacts(): String {
    val symptomsValue = if (symptoms.isEmpty()) {
        MultiStageDefaults.NONE_VALUE
    } else {
        symptoms.joinToString(MultiStageDefaults.SYMPTOM_SEPARATOR)
    }
    val lines = listOf(
        "${MultiStageDefaults.F_AGE}${MultiStageDefaults.PAIR_SEPARATOR}" +
            (ageMonths?.toString() ?: MultiStageDefaults.NONE_VALUE),
        "${MultiStageDefaults.F_SYMPTOMS}${MultiStageDefaults.PAIR_SEPARATOR}$symptomsValue",
        "${MultiStageDefaults.F_METRICS}${MultiStageDefaults.PAIR_SEPARATOR}${metrics.ifBlank { MultiStageDefaults.NONE_VALUE }}",
        "${MultiStageDefaults.F_DURATION}${MultiStageDefaults.PAIR_SEPARATOR}${duration.ifBlank { MultiStageDefaults.NONE_VALUE }}",
        "${MultiStageDefaults.F_PARENT_STATE}${MultiStageDefaults.PAIR_SEPARATOR}" +
            parentState.ifBlank { MultiStageDefaults.NONE_VALUE },
        "${MultiStageDefaults.F_QUESTION_TYPE}${MultiStageDefaults.PAIR_SEPARATOR}${questionType.name}",
    )
    return lines.joinToString("\n")
}

internal fun emptyMultiStageFacts(): MultiStageFactsModel = MultiStageFactsModel(
    ageMonths = null,
    symptoms = emptyList(),
    metrics = MultiStageDefaults.NONE_VALUE,
    duration = MultiStageDefaults.NONE_VALUE,
    parentState = MultiStageDefaults.NONE_VALUE,
    questionType = MultiStageQuestionTypeModel.OTHER,
)

private fun stripCodeFence(rawText: String): String {
    val match = CODE_FENCE_PATTERN.matchEntire(rawText) ?: return rawText
    return match.groupValues[1]
}

private fun collectPairs(text: String, pattern: Regex): Map<String, String> {
    val matches = pattern.findAll(text).toList()
    val pairs = mutableMapOf<String, String>()
    matches.forEachIndexed { index, match ->
        val start = match.range.last + 1
        val end = if (index + 1 < matches.size) matches[index + 1].range.first else text.length
        val key = match.groupValues[1].uppercase()
        pairs[key] = text.substring(start, end)
    }
    return pairs
}

private fun isNoneValue(value: String): Boolean =
    value.trim().trim { char -> char in VALUE_TAIL_CHARS }.lowercase() in NONE_ALIASES

private fun cleanValue(value: String): String =
    value.trim().trim { char -> char in VALUE_TAIL_CHARS }.trim()

private fun clipValue(value: String, limit: Int): String =
    if (value.length <= limit) value else value.substring(0, limit)

private fun parseAge(value: String?): Pair<Int?, Boolean> {
    if (value == null || isNoneValue(value)) return null to false
    val age = INTEGER_PATTERN.find(value)?.value?.toInt()
    return when {
        age == null -> null to false
        age < MultiStageDefaults.MIN_AGE_MONTHS || age > MultiStageDefaults.MAX_AGE_MONTHS -> null to true
        else -> age to false
    }
}

private fun parseSymptoms(value: String?): List<String> {
    if (value == null || isNoneValue(value)) return emptyList()
    val parts = value.split(MultiStageDefaults.SYMPTOM_SEPARATOR).map { part -> cleanValue(part) }
    val symptoms = parts
        .filter { part -> part.isNotEmpty() && !isNoneValue(part) }
        .map { part -> clipValue(part, MultiStageDefaults.MAX_SYMPTOM_CHARS) }
    return symptoms.take(MultiStageDefaults.MAX_SYMPTOMS)
}

private fun parseFreeField(value: String?, limit: Int): String {
    if (value == null || isNoneValue(value)) return MultiStageDefaults.NONE_VALUE
    val cleaned = cleanValue(value)
        .split(Regex("\\s+"))
        .filter { part -> part.isNotEmpty() }
        .joinToString(" ")
    if (cleaned.isEmpty()) return MultiStageDefaults.NONE_VALUE
    return clipValue(cleaned, limit)
}

private fun parseQuestionType(value: String?): Pair<MultiStageQuestionTypeModel, Boolean> {
    if (value == null) return MultiStageQuestionTypeModel.OTHER to true
    val candidateName = WORD_PATTERN.find(value)?.value?.uppercase()
    val questionType = MultiStageQuestionTypeModel.entries.find { type -> type.name == candidateName }
    return if (questionType != null) questionType to false else MultiStageQuestionTypeModel.OTHER to true
}

private fun parseConfidence(value: String?): Pair<Double, Boolean> {
    if (value == null) return 0.0 to true
    val number = NUMBER_PATTERN.find(value)?.value?.replace(",", ".")?.toDouble()
    return when {
        number == null -> 0.0 to true
        number < MultiStageDefaults.MIN_CONFIDENCE || number > MultiStageDefaults.MAX_CONFIDENCE ->
            number.coerceIn(MultiStageDefaults.MIN_CONFIDENCE, MultiStageDefaults.MAX_CONFIDENCE) to true
        else -> number to false
    }
}

private fun routeLeaked(rawText: String): Boolean = LEAK_PATTERN.containsMatchIn(rawText)

private fun parseRouteValue(value: String?): TriageRouteModel? {
    if (value == null) return null
    val match = LEAK_PATTERN.find(value) ?: return null
    return match.groupValues[1].uppercase().toKnownTriageRouteModel()
}

private fun String.toKnownTriageRouteModel(): TriageRouteModel? =
    TriageRouteModel.entries.find { route -> route.name == this && route != TriageRouteModel.UNKNOWN }
