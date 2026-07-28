package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.ChatChoiceResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatChunkChoiceResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatChunkDeltaResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatCompletionChunkResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageResponseModel
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class AiDataMappersTest {

    @Test
    fun toChatMessageModel_takesFirstChoiceAndTrimsContent() {
        val response = responseWith("  Hello there  ", "second choice")

        val result = response.toChatMessageModel()

        assertEquals("Hello there", result.text)
    }

    @Test
    fun toChatMessageModel_alwaysMarksAuthorAsAssistant() {
        val response = responseWith("anything")

        val result = response.toChatMessageModel()

        assertEquals(MessageAuthor.ASSISTANT, result.author)
    }

    @Test
    fun toChatMessageModel_withoutChoices_returnsEmptyText() {
        val response = ChatCompletionResponseModel(choices = emptyList())

        val result = response.toChatMessageModel()

        assertEquals("", result.text)
        assertEquals(MessageAuthor.ASSISTANT, result.author)
    }

    @Test
    fun toChatMessageModel_blankContent_collapsesToEmptyText() {
        val response = responseWith("   \n  ")

        val result = response.toChatMessageModel()

        assertEquals("", result.text)
    }

    @Test
    fun toChatMessageRequestModel_mapsUserAuthorToUserRole() {
        val message = ChatMessageModel(author = MessageAuthor.USER, text = "ping")

        val result = message.toChatMessageRequestModel()

        assertEquals("user", result.role)
        assertEquals("ping", result.content)
    }

    @Test
    fun toChatMessageRequestModel_mapsAssistantAuthorToAssistantRole() {
        val message = ChatMessageModel(author = MessageAuthor.ASSISTANT, text = "pong")

        val result = message.toChatMessageRequestModel()

        assertEquals("assistant", result.role)
        assertEquals("pong", result.content)
    }

    @Test
    fun toChatMessageRequestModel_keepsContentUntrimmed() {
        val message = ChatMessageModel(author = MessageAuthor.USER, text = "  spaced  ")

        val result = message.toChatMessageRequestModel()

        assertEquals("  spaced  ", result.content)
    }

    @Test
    fun toDeltaTextOrNull_withContent_returnsContent() {
        val chunk = chunkWith(content = "Hel")

        assertEquals("Hel", chunk.toDeltaTextOrNull())
    }

    @Test
    fun toDeltaTextOrNull_withEmptyContent_returnsNull() {
        val chunk = chunkWith(content = "")

        assertNull(chunk.toDeltaTextOrNull())
    }

    @Test
    fun toDeltaTextOrNull_withNullContent_returnsNull() {
        val chunk = chunkWith(content = null)

        assertNull(chunk.toDeltaTextOrNull())
    }

    @Test
    fun toDeltaTextOrNull_withoutChoices_returnsNull() {
        val chunk = ChatCompletionChunkResponseModel(choices = emptyList())

        assertNull(chunk.toDeltaTextOrNull())
    }

    @Test
    fun toChatStreamChunkDataModelOrNull_withContentAndModel_carriesBoth() {
        val chunk = chunkWith(content = "Hel", model = "deepseek-chat")

        val result = chunk.toChatStreamChunkDataModelOrNull()

        assertEquals("Hel", result?.text)
        assertEquals("deepseek-chat", result?.modelId)
    }

    @Test
    fun toChatStreamChunkDataModelOrNull_withOnlyModel_returnsEmptyTextWithModelId() {
        val chunk = chunkWith(content = null, model = "deepseek-chat")

        val result = chunk.toChatStreamChunkDataModelOrNull()

        assertEquals("", result?.text)
        assertEquals("deepseek-chat", result?.modelId)
    }

    @Test
    fun toChatStreamChunkDataModelOrNull_withoutContentAndModel_returnsNull() {
        val chunk = chunkWith(content = null, model = null)

        assertNull(chunk.toChatStreamChunkDataModelOrNull())
    }

    private fun chunkWith(content: String?, model: String? = null): ChatCompletionChunkResponseModel =
        ChatCompletionChunkResponseModel(
            choices = listOf(
                ChatChunkChoiceResponseModel(
                    delta = ChatChunkDeltaResponseModel(content = content),
                ),
            ),
            model = model,
        )

    private fun responseWith(vararg contents: String): ChatCompletionResponseModel =
        ChatCompletionResponseModel(
            choices = contents.map { content ->
                ChatChoiceResponseModel(
                    message = ChatMessageResponseModel(role = "assistant", content = content),
                )
            },
        )
}
