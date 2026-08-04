package com.jarvis.chat.feature.chat.data.mapper

import com.jarvis.chat.feature.chat.data.model.ChatMessageDataModel
import com.jarvis.chat.feature.chat.domain.model.ImportMessageVerdictModel
import com.jarvis.chat.feature.chat.domain.model.ImportRejectionReasonModel

private val MARKUP_COMMENT_PATTERN = Regex("<!--.*?-->", RegexOption.DOT_MATCHES_ALL)
private val STYLE_SPAN_PATTERN = Regex(
    "<span[^>]*style=\"[^\"]*\"[^>]*>.*?</span>",
    setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE),
)
private val FORMAT_OR_CONTROL_CHAR_PATTERN = Regex("[\\p{Cc}\\p{Cf}]")
private val WHITESPACE_PATTERN = Regex("\\s+")

private const val DENSE_INVISIBLE_CHAR_THRESHOLD = 3
internal const val MAX_IMPORTED_MESSAGE_CHARS = 4_000

internal fun ChatMessageDataModel.toImportVerdict(isTextAllowed: (String) -> Boolean): ImportMessageVerdictModel {
    val concealmentReason = detectConcealment(text)
    if (concealmentReason != null) {
        return ImportMessageVerdictModel.Rejected(concealmentReason)
    }
    val cleanedText = FORMAT_OR_CONTROL_CHAR_PATTERN.replace(text, "")
    val wasTruncated = cleanedText.length > MAX_IMPORTED_MESSAGE_CHARS
    val boundedText = cleanedText.take(MAX_IMPORTED_MESSAGE_CHARS)
    if (boundedText.isNotBlank() && !isTextAllowed(boundedText)) {
        return ImportMessageVerdictModel.Rejected(ImportRejectionReasonModel.INPUT_GUARD_BLOCKED)
    }
    val sanitizedMessage = copy(text = boundedText).toHistoryMessageModel(isImported = true)
    return ImportMessageVerdictModel.Accepted(message = sanitizedMessage, wasTruncated = wasTruncated)
}

private fun detectConcealment(text: String): ImportRejectionReasonModel? = when {
    hasHiddenMarkup(text) -> ImportRejectionReasonModel.HIDDEN_MARKUP
    hasDenseInvisibleChars(text) -> ImportRejectionReasonModel.DENSE_INVISIBLE_CHARS
    else -> null
}

private fun hasHiddenMarkup(text: String): Boolean =
    MARKUP_COMMENT_PATTERN.containsMatchIn(text) || STYLE_SPAN_PATTERN.containsMatchIn(text)

private fun hasDenseInvisibleChars(text: String): Boolean =
    text.split(WHITESPACE_PATTERN).any { token -> FORMAT_OR_CONTROL_CHAR_PATTERN.findAll(token).count() >= DENSE_INVISIBLE_CHAR_THRESHOLD }
