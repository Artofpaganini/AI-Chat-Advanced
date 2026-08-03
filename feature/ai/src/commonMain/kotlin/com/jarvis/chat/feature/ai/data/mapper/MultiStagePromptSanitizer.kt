package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.di.MultiStageDefaults
import com.jarvis.chat.feature.ai.domain.model.MultiStageFactsModel

private val CONTROL_CHAR_PATTERN = Regex("[\\p{Cc}\\p{Cf}]")
private val BRACKETED_INSTRUCTION_PATTERN = Regex("\\[[^\\[\\]]{0,200}\\]")

private val DIRECTIVE_MARKER_WORDS = setOf(
    "SYSTEM",
    "ASSISTANT",
    "INSTRUCTION",
    "USER",
    MultiStageDefaults.F_AGE,
    MultiStageDefaults.F_SYMPTOMS,
    MultiStageDefaults.F_METRICS,
    MultiStageDefaults.F_DURATION,
    MultiStageDefaults.F_PARENT_STATE,
    MultiStageDefaults.F_QUESTION_TYPE,
    MultiStageDefaults.D_ROUTE,
    MultiStageDefaults.D_CONFIDENCE,
    MultiStageDefaults.D_WHY,
)

private val DIRECTIVE_MARKER_PATTERN = Regex(
    "(?<![A-Za-z_])(${DIRECTIVE_MARKER_WORDS.joinToString("|")})\\s*[=:]",
    RegexOption.IGNORE_CASE,
)

private val CHILD_RED_FLAG_STEM_PATTERN = Regex(
    "дыш|вдохн|выдохн|втяжен|синюшн|посине|судорог|сознани|вял|разбуди|" +
        "температур|сыпь|обезвож|травм|рвот|проглот|кровотечен",
)

internal fun sanitizeStageValue(value: String): String {
    val withoutDirectives = value
        .replace(CONTROL_CHAR_PATTERN, " ")
        .replace(BRACKETED_INSTRUCTION_PATTERN, " ")
        .replace(DIRECTIVE_MARKER_PATTERN, " ")
        .replace(MultiStageDefaults.USER_INPUT_START, " ", ignoreCase = true)
        .replace(MultiStageDefaults.USER_INPUT_END, " ", ignoreCase = true)
    return withoutDirectives
        .split(Regex("\\s+"))
        .filter { part -> part.isNotEmpty() }
        .joinToString(" ")
}

internal fun String.escapeBoundaryMarkers(): String =
    this
        .replace(MultiStageDefaults.USER_INPUT_START, " ", ignoreCase = true)
        .replace(MultiStageDefaults.USER_INPUT_END, " ", ignoreCase = true)

internal fun childRedFlagWordsMissingFromSymptoms(caseText: String, facts: MultiStageFactsModel): Boolean =
    facts.symptoms.isEmpty() && CHILD_RED_FLAG_STEM_PATTERN.containsMatchIn(caseText.lowercase())
