package com.jarvis.chat.feature.ai.data.repository

import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSource
import com.jarvis.chat.feature.ai.data.model.ChatChoiceResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageResponseModel
import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.AiException
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import io.ktor.client.plugins.HttpRequestTimeoutException
import io.ktor.client.request.HttpRequestBuilder
import kotlinx.coroutines.test.runTest
import kotlinx.io.IOException
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class AiRepositoryImplTest {

    @Test
    fun sendMessage_forwardsHistoryAsRequestMessagesInSameOrder() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(reply = "ok")
        val repository = AiRepositoryImpl(remoteDataSource = dataSource)

        repository.sendMessage(
            listOf(
                ChatMessageModel(author = MessageAuthor.USER, text = "first"),
                ChatMessageModel(author = MessageAuthor.ASSISTANT, text = "second"),
                ChatMessageModel(author = MessageAuthor.USER, text = "third"),
            ),
        )

        assertEquals(
            listOf("user" to "first", "assistant" to "second", "user" to "third"),
            dataSource.received.map { message -> message.role to message.content },
        )
    }

    @Test
    fun sendMessage_mapsResponseToAssistantMessage() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(reply = "  answer  ")
        val repository = AiRepositoryImpl(remoteDataSource = dataSource)

        val result = repository.sendMessage(
            listOf(ChatMessageModel(author = MessageAuthor.USER, text = "question")),
        )

        assertEquals(MessageAuthor.ASSISTANT, result.author)
        assertEquals("answer", result.text)
    }

    @Test
    fun sendMessage_withEmptyHistory_stillCallsDataSource() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(reply = "hi")
        val repository = AiRepositoryImpl(remoteDataSource = dataSource)

        val result = repository.sendMessage(emptyList())

        assertTrue(dataSource.received.isEmpty())
        assertEquals("hi", result.text)
    }

    @Test
    fun sendMessage_whenDataSourceFails_throwsAiExceptionWithMappedError() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(error = IllegalStateException("network down"))
        val repository = AiRepositoryImpl(remoteDataSource = dataSource)

        val error = assertFailsWith<AiException> {
            repository.sendMessage(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "x")))
        }

        assertEquals(AiErrorModel.Unknown, error.error)
    }

    @Test
    fun sendMessage_whenDataSourceFailsWithIoException_throwsAiExceptionWithNoConnection() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(error = IOException("network down"))
        val repository = AiRepositoryImpl(remoteDataSource = dataSource)

        val error = assertFailsWith<AiException> {
            repository.sendMessage(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "x")))
        }

        assertEquals(AiErrorModel.NoConnection, error.error)
    }

    @Test
    fun sendMessage_whenDataSourceFailsWithTimeout_throwsAiExceptionWithTimeout() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(error = HttpRequestTimeoutException(HttpRequestBuilder()))
        val repository = AiRepositoryImpl(remoteDataSource = dataSource)

        val error = assertFailsWith<AiException> {
            repository.sendMessage(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "x")))
        }

        assertEquals(AiErrorModel.Timeout, error.error)
    }

    @Test
    fun sendMessage_whenResponseHasNoChoices_returnsEmptyText() = runTest {
        val dataSource = FakeDeepSeekRemoteDataSource(reply = null)
        val repository = AiRepositoryImpl(remoteDataSource = dataSource)

        val result = repository.sendMessage(
            listOf(ChatMessageModel(author = MessageAuthor.USER, text = "x")),
        )

        assertEquals("", result.text)
    }

    private class FakeDeepSeekRemoteDataSource(
        private val reply: String? = null,
        private val error: Throwable? = null,
    ) : DeepSeekRemoteDataSource {

        val received: MutableList<ChatMessageRequestModel> = mutableListOf()

        override suspend fun requestCompletion(
            messages: List<ChatMessageRequestModel>,
        ): ChatCompletionResponseModel {
            received += messages
            error?.let { failure -> throw failure }
            val choices = reply?.let { content ->
                listOf(
                    ChatChoiceResponseModel(
                        message = ChatMessageResponseModel(role = "assistant", content = content),
                    ),
                )
            }.orEmpty()
            return ChatCompletionResponseModel(choices = choices)
        }
    }
}
