package com.jarvis.chat.feature.chat.presentation.ui

private const val CODE_BLOCK_SPEECH_PLACEHOLDER = "Code block."
private const val SPEECH_BLOCK_SEPARATOR = "\n"

internal fun buildSpeechText(source: String): String =
    parseMarkdown(source)
        .map { block -> block.toSpeechText() }
        .filter { text -> text.isNotBlank() }
        .joinToString(separator = SPEECH_BLOCK_SEPARATOR)

private fun MarkdownBlock.toSpeechText(): String = when (this) {
    is MarkdownBlock.Paragraph -> spans.toSpeechText()
    is MarkdownBlock.Heading -> spans.toSpeechText()
    is MarkdownBlock.BulletItem -> spans.toSpeechText()
    is MarkdownBlock.NumberedItem -> spans.toSpeechText()
    is MarkdownBlock.CodeBlock -> CODE_BLOCK_SPEECH_PLACEHOLDER
}

private fun List<MarkdownSpan>.toSpeechText(): String =
    joinToString(separator = "") { span -> span.text }
