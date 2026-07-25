package com.jarvis.chat.feature.chat.presentation.ui

import kotlin.test.Test
import kotlin.test.assertEquals

class MarkdownSpeechTextTest {

    @Test
    fun buildSpeechText_emptyText_returnsEmptyString() {
        val speechText = buildSpeechText("")

        assertEquals("", speechText)
    }

    @Test
    fun buildSpeechText_plainText_returnsTextUnchanged() {
        val speechText = buildSpeechText("hello world")

        assertEquals("hello world", speechText)
    }

    @Test
    fun buildSpeechText_boldMarker_stripsMarkersAndKeepsText() {
        val speechText = buildSpeechText("**bold**")

        assertEquals("bold", speechText)
    }

    @Test
    fun buildSpeechText_italicMarker_stripsMarkersAndKeepsText() {
        val speechText = buildSpeechText("*italic*")

        assertEquals("italic", speechText)
    }

    @Test
    fun buildSpeechText_inlineCode_stripsMarkersAndKeepsText() {
        val speechText = buildSpeechText("`code`")

        assertEquals("code", speechText)
    }

    @Test
    fun buildSpeechText_mixedInlineFormatting_stripsAllMarkersAndKeepsPlainWords() {
        val speechText = buildSpeechText("plain **bold** and `code`")

        assertEquals("plain bold and code", speechText)
    }

    @Test
    fun buildSpeechText_heading_readsAsPlainSentenceWithoutHashMarker() {
        val speechText = buildSpeechText("# Title")

        assertEquals("Title", speechText)
    }

    @Test
    fun buildSpeechText_bulletList_readsItemsAsPlainSentencesWithoutBulletMarker() {
        val speechText = buildSpeechText("- first\n- second")

        assertEquals("first\nsecond", speechText)
    }

    @Test
    fun buildSpeechText_numberedList_readsItemsAsPlainSentencesWithoutNumberPrefix() {
        val speechText = buildSpeechText("1. first\n2. second")

        assertEquals("first\nsecond", speechText)
    }

    @Test
    fun buildSpeechText_codeBlock_replacesContentWithPlaceholder() {
        val speechText = buildSpeechText("```kotlin\nval x = 1\n```")

        assertEquals("Code block.", speechText)
    }

    @Test
    fun buildSpeechText_mixedContentWithCodeBlock_skipsCodeContentAndKeepsSurroundingText() {
        val source = "intro\n```\ncode here\n```\noutro"

        val speechText = buildSpeechText(source)

        assertEquals("intro\nCode block.\noutro", speechText)
    }
}
