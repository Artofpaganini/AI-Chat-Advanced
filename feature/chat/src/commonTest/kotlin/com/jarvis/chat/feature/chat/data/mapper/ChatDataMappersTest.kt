package com.jarvis.chat.feature.chat.data.mapper

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.data.model.ChatMessageDataModel
import com.jarvis.chat.feature.chat.domain.mapper.toChatMessageModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import kotlin.test.Test
import kotlin.test.assertEquals

private const val EXPECTED_HISTORY_VERSION = 1

class ChatDataMappersTest {

    @Test
    fun toChatMessageDataModel_encodesAuthorAsString() {
        val user = message(author = MessageAuthor.USER).toChatMessageDataModel()
        val assistant = message(author = MessageAuthor.ASSISTANT).toChatMessageDataModel()

        assertEquals("USER", user.author)
        assertEquals("ASSISTANT", assistant.author)
    }

    @Test
    fun toChatMessageDataModel_preservesScalarFields() {
        val model = HistoryMessageModel(
            id = "m1",
            author = MessageAuthor.ASSISTANT,
            text = "answer",
            isFavorite = true,
            timestamp = TEST_TIMESTAMP,
        )

        val dataModel = model.toChatMessageDataModel()

        assertEquals("m1", dataModel.id)
        assertEquals("answer", dataModel.text)
        assertEquals(true, dataModel.isFavorite)
    }

    @Test
    fun toHistoryMessageModel_decodesKnownAuthors() {
        val assistant = dataModel(author = "ASSISTANT").toHistoryMessageModel()
        val user = dataModel(author = "USER").toHistoryMessageModel()

        assertEquals(MessageAuthor.ASSISTANT, assistant.author)
        assertEquals(MessageAuthor.USER, user.author)
    }

    @Test
    fun toHistoryMessageModel_unknownAuthorFallsBackToUser() {
        val decoded = dataModel(author = "SYSTEM").toHistoryMessageModel()

        assertEquals(MessageAuthor.USER, decoded.author)
    }

    @Test
    fun modelToDataAndBack_roundTripsForBothAuthors() {
        val original = listOf(
            HistoryMessageModel(
                id = "u1",
                author = MessageAuthor.USER,
                text = "q",
                isFavorite = false,
                timestamp = TEST_TIMESTAMP,
            ),
            HistoryMessageModel(
                id = "a1",
                author = MessageAuthor.ASSISTANT,
                text = "a",
                isFavorite = true,
                timestamp = TEST_TIMESTAMP,
            ),
        )

        val roundTripped = original
            .map { message -> message.toChatMessageDataModel() }
            .map { dataModel -> dataModel.toHistoryMessageModel() }

        assertEquals(original, roundTripped)
    }

    @Test
    fun listToChatHistoryDataModel_setsVersionAndPreservesOrder() {
        val messages = listOf(
            HistoryMessageModel(
                id = "1",
                author = MessageAuthor.USER,
                text = "a",
                isFavorite = false,
                timestamp = TEST_TIMESTAMP,
            ),
            HistoryMessageModel(
                id = "2",
                author = MessageAuthor.ASSISTANT,
                text = "b",
                isFavorite = false,
                timestamp = TEST_TIMESTAMP,
            ),
        )

        val history = messages.toChatHistoryDataModel()

        assertEquals(EXPECTED_HISTORY_VERSION, history.version)
        assertEquals(listOf("1", "2"), history.messages.map { message -> message.id })
    }

    @Test
    fun toChatMessageModel_dropsHistoryOnlyFieldsAndKeepsAuthorAndText() {
        val historyMessage = HistoryMessageModel(
            id = "m1",
            author = MessageAuthor.ASSISTANT,
            text = "keep me",
            isFavorite = true,
            timestamp = TEST_TIMESTAMP,
        )

        val chatMessage = historyMessage.toChatMessageModel()

        assertEquals(MessageAuthor.ASSISTANT, chatMessage.author)
        assertEquals("keep me", chatMessage.text)
    }

    private fun message(author: MessageAuthor): HistoryMessageModel =
        HistoryMessageModel(id = "id", author = author, text = "text", isFavorite = false, timestamp = TEST_TIMESTAMP)

    private fun dataModel(author: String): ChatMessageDataModel =
        ChatMessageDataModel(id = "id", author = author, text = "text", isFavorite = false)
}

private const val TEST_TIMESTAMP = 1_700_000_000_000L
