package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.domain.model.InputGuardResultModel
import kotlin.io.encoding.Base64

private val BASE64_CANDIDATE_PATTERN = Regex("[A-Za-z0-9+/]{24,}={0,2}")
private val LATIN_RUN_PATTERN = Regex("[A-Za-z][A-Za-z ,.'\"!?;:]*[A-Za-z]")
private val LETTER_RUN_PATTERN = Regex("(?:[a-zA-Zа-яА-ЯёЁ][ \\-]){4,}[a-zA-Zа-яА-ЯёЁ]")
private val LETTER_RUN_SEPARATOR_PATTERN = Regex("[ \\-]")

private const val MIN_ROT13_LETTERS = 20
private const val MIN_PRINTABLE_RATIO = 0.85
private const val ROT13_ROTATION = 13
private const val ALPHABET_SIZE = 26
private const val MIN_ROT13_COMMON_WORDS = 2
private const val BASE64_BLOCK_SIZE = 4

private val COMMON_ENGLISH_WORDS = listOf(
    "the",
    "you",
    "your",
    "and",
    "are",
    "is",
    "to",
    "instructions",
    "ignore",
    "system",
    "this",
    "that",
    "with",
    "for",
    "not",
    "have",
    "will",
    "print",
    "reveal",
    "developer",
    "mode",
    "content",
    "policy",
    "all",
    "previous",
    "prompt",
)

private val OVERRIDE_VERB_STEMS = listOf(
    "игнориру",
    "забуд",
    "отмени",
    "перепиш",
    "не признаю",
    "не выполня",
    "ignore",
    "forget",
    "disregard",
    "override",
    "bypass",
    "вывед",
    "вывод",
    "покажи",
    "раскрой",
    "раскры",
    "повтор",
    "reveal",
    "show",
    "print",
    "output",
    "display",
    "repeat",
)
private val INSTRUCTION_TARGET_STEMS = listOf(
    "инструкц",
    "правил",
    "промпт",
    "ограничен",
    "instruction",
    "system prompt",
    "rule",
    "restriction",
    "guideline",
)
private val PERSONA_SIGNAL_PHRASES = listOf(
    "developer mode",
    "dan mode",
    "do anything now",
    "режим разработчика",
    "no content policy",
    "no restrictions",
    "without any restrictions",
    "without restrictions",
    "you are dan",
    "i am dan",
    "unfiltered ai",
    "без цензуры",
    "без фильтров",
)

private const val INPUT_GUARD_BLOCKED_MESSAGE =
    "Сообщение отклонено фильтром входа: в нём обнаружена закодированная строка с признаком " +
        "попытки обойти инструкции."

internal fun checkInputGuard(rawText: String): InputGuardResultModel {
    val layers = extractDecodedLayers(rawText)
    val chunksToCheck = buildList {
        add(rawText)
        addAll(layers)
        if (layers.size > 1) {
            add(layers.joinToString(" "))
        }
    }
    val isBlocked = chunksToCheck.any { chunk -> injectionSignalReason(chunk).isNotEmpty() }
    return if (isBlocked) {
        InputGuardResultModel.Blocked(reason = INPUT_GUARD_BLOCKED_MESSAGE)
    } else {
        InputGuardResultModel.Allowed
    }
}

private fun extractDecodedLayers(text: String): List<String> =
    decodeBase64Candidates(text) + decodeLetterSpaced(text) + decodeRot13Candidates(text)

private fun decodeBase64Candidates(text: String): List<String> =
    BASE64_CANDIDATE_PATTERN.findAll(text).mapNotNull { match -> match.value.decodeBase64OrNull() }.toList()

private fun String.decodeBase64OrNull(): String? {
    val paddingNeeded = (BASE64_BLOCK_SIZE - length % BASE64_BLOCK_SIZE) % BASE64_BLOCK_SIZE
    val padded = this + "=".repeat(paddingNeeded)
    val decodedText = runCatching {
        Base64.Default.decode(padded).decodeToString(throwOnInvalidSequence = true)
    }.getOrNull() ?: return null
    if (decodedText.isBlank() || decodedText.printableRatio() < MIN_PRINTABLE_RATIO) {
        return null
    }
    return decodedText
}

private fun String.printableRatio(): Double {
    if (isEmpty()) {
        return 0.0
    }
    val printableCount = count { char -> char.isPrintableForGuard() }
    return printableCount.toDouble() / length
}

private const val MIN_PRINTABLE_CODE_POINT = 0x20
private const val DELETE_CODE_POINT = 0x7F

private fun Char.isPrintableForGuard(): Boolean =
    this == '\n' || this == '\r' || this == '\t' || (code >= MIN_PRINTABLE_CODE_POINT && code != DELETE_CODE_POINT)

private fun decodeLetterSpaced(text: String): List<String> =
    LETTER_RUN_PATTERN.findAll(text)
        .map { match -> match.value.replace(LETTER_RUN_SEPARATOR_PATTERN, "") }
        .toList()

private fun decodeRot13Candidates(text: String): List<String> {
    val decoded = mutableListOf<String>()
    for (match in LATIN_RUN_PATTERN.findAll(text)) {
        val original = match.value
        val letterCount = original.count { char -> char.isLetter() }
        if (letterCount < MIN_ROT13_LETTERS) {
            continue
        }
        val rotated = original.rot13()
        val originalWordCount = original.countCommonWords()
        val rotatedWordCount = rotated.countCommonWords()
        if (rotatedWordCount > originalWordCount && rotatedWordCount >= MIN_ROT13_COMMON_WORDS) {
            decoded.add(rotated)
        }
    }
    return decoded
}

private fun String.rot13(): String =
    map { char ->
        when (char) {
            in 'a'..'z' -> 'a' + (char - 'a' + ROT13_ROTATION) % ALPHABET_SIZE
            in 'A'..'Z' -> 'A' + (char - 'A' + ROT13_ROTATION) % ALPHABET_SIZE
            else -> char
        }
    }.joinToString("")

private fun String.countCommonWords(): Int {
    val lowered = lowercase()
    return COMMON_ENGLISH_WORDS.count { word -> lowered.contains(word) }
}

private fun injectionSignalReason(text: String): String {
    val lowered = text.lowercase()
    val hasOverride = OVERRIDE_VERB_STEMS.any { stem -> lowered.contains(stem) }
    val hasTarget = INSTRUCTION_TARGET_STEMS.any { stem -> lowered.contains(stem) }
    if (hasOverride && hasTarget) {
        return "override_verb_plus_instruction_target"
    }
    val personaPhrase = PERSONA_SIGNAL_PHRASES.firstOrNull { phrase -> lowered.contains(phrase) }
    return if (personaPhrase != null) "persona_signal_${personaPhrase.replace(" ", "_")}" else ""
}
