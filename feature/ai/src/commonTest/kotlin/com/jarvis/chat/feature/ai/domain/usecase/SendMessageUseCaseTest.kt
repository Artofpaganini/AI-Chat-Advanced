package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class SendMessageUseCaseTest {

    @Test
    fun invoke_onSuccess_returnsReplyAndForwardsHistory() = runTest {
        val reply = ChatMessageModel(author = MessageAuthor.ASSISTANT, text = "hi there")
        val repository = FakeAiRepository(reply = reply)
        val history = listOf(ChatMessageModel(author = MessageAuthor.USER, text = "hello"))

        val result = SendMessageUseCase(repository).invoke(history)

        assertEquals(reply, result.getOrNull())
        assertEquals(history, repository.lastHistory)
    }

    @Test
    fun invoke_onRepositoryFailure_returnsFailureAndDoesNotThrow() = runTest {
        val repository = FakeAiRepository(error = IllegalStateException("network down"))

        val result = SendMessageUseCase(repository)
            .invoke(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "hello")))

        assertTrue(result.isFailure)
        assertEquals("network down", result.exceptionOrNull()?.message)
    }

    @Test
    fun invoke_onCancellation_rethrowsInsteadOfWrappingInResult() = runTest {
        val repository = FakeAiRepository(error = CancellationException("request cancelled"))

        assertFailsWith<CancellationException> {
            SendMessageUseCase(repository)
                .invoke(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "hello")))
        }
    }
}

private class FakeAiRepository(
    private val reply: ChatMessageModel = ChatMessageModel(MessageAuthor.ASSISTANT, "reply"),
    private val error: Throwable? = null,
) : AiRepository {

    var lastHistory: List<ChatMessageModel>? = null
        private set

    override suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel {
        lastHistory = history
        error?.let { failure -> throw failure }
        return reply
    }

    override fun sendMessageStream(history: List<ChatMessageModel>): Flow<String> = flow {
        lastHistory = history
        error?.let { failure -> throw failure }
        emit(reply.text)
    }
}
