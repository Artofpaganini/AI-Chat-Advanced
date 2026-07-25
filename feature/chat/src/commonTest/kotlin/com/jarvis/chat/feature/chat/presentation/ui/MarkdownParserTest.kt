package com.jarvis.chat.feature.chat.presentation.ui

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertTrue

class MarkdownParserTest {

    @Test
    fun parseMarkdown_plainText_returnsSingleParagraphWithOriginalTextUnchanged() {
        val blocks = parseMarkdown("hello world")

        val paragraph = assertIs<MarkdownBlock.Paragraph>(blocks.single())
        assertEquals(listOf(MarkdownSpan(text = "hello world")), paragraph.spans)
    }

    @Test
    fun parseMarkdown_emptyText_returnsNoBlocks() {
        val blocks = parseMarkdown("")

        assertTrue(blocks.isEmpty())
    }

    @Test
    fun parseMarkdown_boldMarker_producesBoldSpan() {
        val blocks = parseMarkdown("**bold**")

        val paragraph = assertIs<MarkdownBlock.Paragraph>(blocks.single())
        assertEquals(listOf(MarkdownSpan(text = "bold", isBold = true)), paragraph.spans)
    }

    @Test
    fun parseMarkdown_italicMarkerAsterisk_producesItalicSpan() {
        val blocks = parseMarkdown("*italic*")

        val paragraph = assertIs<MarkdownBlock.Paragraph>(blocks.single())
        assertEquals(listOf(MarkdownSpan(text = "italic", isItalic = true)), paragraph.spans)
    }

    @Test
    fun parseMarkdown_italicMarkerUnderscore_producesItalicSpan() {
        val blocks = parseMarkdown("_italic_")

        val paragraph = assertIs<MarkdownBlock.Paragraph>(blocks.single())
        assertEquals(listOf(MarkdownSpan(text = "italic", isItalic = true)), paragraph.spans)
    }

    @Test
    fun parseMarkdown_inlineCode_producesCodeSpan() {
        val blocks = parseMarkdown("`code`")

        val paragraph = assertIs<MarkdownBlock.Paragraph>(blocks.single())
        assertEquals(listOf(MarkdownSpan(text = "code", isCode = true)), paragraph.spans)
    }

    @Test
    fun parseMarkdown_mixedInlineFormatting_producesOrderedSpans() {
        val blocks = parseMarkdown("plain **bold** and `code`")

        val paragraph = assertIs<MarkdownBlock.Paragraph>(blocks.single())
        assertEquals(
            listOf(
                MarkdownSpan(text = "plain "),
                MarkdownSpan(text = "bold", isBold = true),
                MarkdownSpan(text = " and "),
                MarkdownSpan(text = "code", isCode = true),
            ),
            paragraph.spans,
        )
    }

    @Test
    fun parseMarkdown_unclosedBoldMarker_doesNotCrashAndPreservesLiteralText() {
        val source = "**bold text without closing"

        val blocks = parseMarkdown(source)

        val paragraph = assertIs<MarkdownBlock.Paragraph>(blocks.single())
        assertEquals(listOf(MarkdownSpan(text = source)), paragraph.spans)
    }

    @Test
    fun parseMarkdown_fencedCodeBlockWithLanguage_producesCodeBlockWithLanguage() {
        val blocks = parseMarkdown("```kotlin\nval x = 1\n```")

        val codeBlock = assertIs<MarkdownBlock.CodeBlock>(blocks.single())
        assertEquals("kotlin", codeBlock.language)
        assertEquals("val x = 1", codeBlock.code)
    }

    @Test
    fun parseMarkdown_fencedCodeBlockWithoutLanguage_producesCodeBlockWithNullLanguage() {
        val blocks = parseMarkdown("```\nplain code\n```")

        val codeBlock = assertIs<MarkdownBlock.CodeBlock>(blocks.single())
        assertEquals(null, codeBlock.language)
        assertEquals("plain code", codeBlock.code)
    }

    @Test
    fun parseMarkdown_unterminatedCodeFence_doesNotCrashAndCapturesRemainingLines() {
        val blocks = parseMarkdown("```\nline1\nline2")

        val codeBlock = assertIs<MarkdownBlock.CodeBlock>(blocks.single())
        assertEquals("line1\nline2", codeBlock.code)
    }

    @Test
    fun parseMarkdown_bulletListWithDashPrefix_producesBulletItems() {
        val blocks = parseMarkdown("- first\n- second")

        assertEquals(2, blocks.size)
        val first = assertIs<MarkdownBlock.BulletItem>(blocks[0])
        val second = assertIs<MarkdownBlock.BulletItem>(blocks[1])
        assertEquals(listOf(MarkdownSpan(text = "first")), first.spans)
        assertEquals(listOf(MarkdownSpan(text = "second")), second.spans)
    }

    @Test
    fun parseMarkdown_bulletListWithStarPrefix_producesBulletItems() {
        val blocks = parseMarkdown("* only item")

        val item = assertIs<MarkdownBlock.BulletItem>(blocks.single())
        assertEquals(listOf(MarkdownSpan(text = "only item")), item.spans)
    }

    @Test
    fun parseMarkdown_numberedList_producesNumberedItemsWithCorrectNumbers() {
        val blocks = parseMarkdown("1. first\n2. second")

        assertEquals(2, blocks.size)
        val first = assertIs<MarkdownBlock.NumberedItem>(blocks[0])
        val second = assertIs<MarkdownBlock.NumberedItem>(blocks[1])
        assertEquals(1, first.number)
        assertEquals(2, second.number)
        assertEquals(listOf(MarkdownSpan(text = "first")), first.spans)
        assertEquals(listOf(MarkdownSpan(text = "second")), second.spans)
    }

    @Test
    fun parseMarkdown_headingLevelOne_producesHeadingWithLevelOne() {
        val blocks = parseMarkdown("# Title")

        val heading = assertIs<MarkdownBlock.Heading>(blocks.single())
        assertEquals(1, heading.level)
        assertEquals(listOf(MarkdownSpan(text = "Title")), heading.spans)
    }

    @Test
    fun parseMarkdown_headingLevelTwo_producesHeadingWithLevelTwo() {
        val blocks = parseMarkdown("## Subtitle")

        val heading = assertIs<MarkdownBlock.Heading>(blocks.single())
        assertEquals(2, heading.level)
    }

    @Test
    fun parseMarkdown_headingLevelThree_producesHeadingWithLevelThree() {
        val blocks = parseMarkdown("### Small title")

        val heading = assertIs<MarkdownBlock.Heading>(blocks.single())
        assertEquals(3, heading.level)
    }
}
