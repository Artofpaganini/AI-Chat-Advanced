package com.jarvis.chat.feature.chat.presentation.ui

private const val BOLD_MARKER = "**"
private const val CODE_MARKER = "`"
private const val CODE_FENCE = "```"
private const val BULLET_DASH_PREFIX = "- "
private const val BULLET_STAR_PREFIX = "* "
private const val LINE_SEPARATOR = "\n"
private const val MAX_HEADING_LEVEL = 3

private val HEADING_REGEX = Regex("^(#{1,$MAX_HEADING_LEVEL})\\s+(.*)$")
private val ORDERED_LIST_REGEX = Regex("^(\\d+)\\.\\s+(.*)$")

internal sealed interface MarkdownBlock {
    data class Paragraph(val spans: List<MarkdownSpan>) : MarkdownBlock
    data class Heading(val level: Int, val spans: List<MarkdownSpan>) : MarkdownBlock
    data class BulletItem(val spans: List<MarkdownSpan>) : MarkdownBlock
    data class NumberedItem(val number: Int, val spans: List<MarkdownSpan>) : MarkdownBlock
    data class CodeBlock(val language: String?, val code: String) : MarkdownBlock
}

internal data class MarkdownSpan(
    val text: String,
    val isBold: Boolean = false,
    val isItalic: Boolean = false,
    val isCode: Boolean = false,
)

internal fun parseMarkdown(source: String): List<MarkdownBlock> {
    val blocks = mutableListOf<MarkdownBlock>()
    val paragraphLines = mutableListOf<String>()
    val lines = source.split(LINE_SEPARATOR)

    fun flushParagraph() {
        if (paragraphLines.isNotEmpty()) {
            blocks += MarkdownBlock.Paragraph(spans = parseInlineSpans(paragraphLines.joinToString(LINE_SEPARATOR)))
            paragraphLines.clear()
        }
    }

    var lineIndex = 0
    while (lineIndex < lines.size) {
        val line = lines[lineIndex]
        val trimmedLine = line.trimStart()
        val headingMatch = HEADING_REGEX.find(line)
        val orderedMatch = ORDERED_LIST_REGEX.find(trimmedLine)
        when {
            trimmedLine.startsWith(CODE_FENCE) -> {
                flushParagraph()
                val language = trimmedLine.removePrefix(CODE_FENCE).trim().ifEmpty { null }
                val codeLines = mutableListOf<String>()
                lineIndex++
                while (lineIndex < lines.size && !lines[lineIndex].trimStart().startsWith(CODE_FENCE)) {
                    codeLines += lines[lineIndex]
                    lineIndex++
                }
                blocks += MarkdownBlock.CodeBlock(language = language, code = codeLines.joinToString(LINE_SEPARATOR))
                if (lineIndex < lines.size) {
                    lineIndex++
                }
            }

            headingMatch != null -> {
                flushParagraph()
                val level = headingMatch.groupValues[1].length
                val content = headingMatch.groupValues[2]
                blocks += MarkdownBlock.Heading(level = level, spans = parseInlineSpans(content))
                lineIndex++
            }

            trimmedLine.startsWith(BULLET_DASH_PREFIX) || trimmedLine.startsWith(BULLET_STAR_PREFIX) -> {
                flushParagraph()
                val content = trimmedLine.drop(BULLET_DASH_PREFIX.length)
                blocks += MarkdownBlock.BulletItem(spans = parseInlineSpans(content))
                lineIndex++
            }

            orderedMatch != null -> {
                flushParagraph()
                val number = orderedMatch.groupValues[1].toInt()
                val content = orderedMatch.groupValues[2]
                blocks += MarkdownBlock.NumberedItem(number = number, spans = parseInlineSpans(content))
                lineIndex++
            }

            line.isBlank() -> {
                flushParagraph()
                lineIndex++
            }

            else -> {
                paragraphLines += line
                lineIndex++
            }
        }
    }
    flushParagraph()
    return blocks
}

private fun parseInlineSpans(text: String): List<MarkdownSpan> {
    val spans = mutableListOf<MarkdownSpan>()
    val plainBuilder = StringBuilder()

    fun flushPlain() {
        if (plainBuilder.isNotEmpty()) {
            spans += MarkdownSpan(text = plainBuilder.toString())
            plainBuilder.clear()
        }
    }

    var charIndex = 0
    while (charIndex < text.length) {
        val currentChar = text[charIndex]
        when {
            text.startsWith(BOLD_MARKER, charIndex) -> {
                val closingIndex = text.indexOf(BOLD_MARKER, charIndex + BOLD_MARKER.length)
                if (closingIndex == -1) {
                    plainBuilder.append(currentChar)
                    charIndex++
                } else {
                    flushPlain()
                    spans += MarkdownSpan(
                        text = text.substring(charIndex + BOLD_MARKER.length, closingIndex),
                        isBold = true,
                    )
                    charIndex = closingIndex + BOLD_MARKER.length
                }
            }

            text.startsWith(CODE_MARKER, charIndex) -> {
                val closingIndex = text.indexOf(CODE_MARKER, charIndex + CODE_MARKER.length)
                if (closingIndex == -1) {
                    plainBuilder.append(currentChar)
                    charIndex++
                } else {
                    flushPlain()
                    spans += MarkdownSpan(
                        text = text.substring(charIndex + CODE_MARKER.length, closingIndex),
                        isCode = true,
                    )
                    charIndex = closingIndex + CODE_MARKER.length
                }
            }

            currentChar == '*' || currentChar == '_' -> {
                val closingIndex = text.indexOf(currentChar, charIndex + 1)
                if (closingIndex == -1 || closingIndex == charIndex + 1) {
                    plainBuilder.append(currentChar)
                    charIndex++
                } else {
                    flushPlain()
                    spans += MarkdownSpan(
                        text = text.substring(charIndex + 1, closingIndex),
                        isItalic = true,
                    )
                    charIndex = closingIndex + 1
                }
            }

            else -> {
                plainBuilder.append(currentChar)
                charIndex++
            }
        }
    }
    flushPlain()
    return spans
}
