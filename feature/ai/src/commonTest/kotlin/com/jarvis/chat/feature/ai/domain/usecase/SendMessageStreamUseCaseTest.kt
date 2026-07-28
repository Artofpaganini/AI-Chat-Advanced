package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.ChatStreamChunkModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class SendMessageStreamUseCaseTest {

    @Test
    fun invoke_forwardsHistoryAndEmitsChunksFromRepository() = runTest {
        val repository = FakeStreamAiRepository(chunks = listOf("Hel", "lo"))
        val history = listOf(ChatMessageModel(author = MessageAuthor.USER, text = "hello"))

        val chunks = SendMessageStreamUseCase(repository).invoke(history).toList()

        assertEquals(listOf("Hel", "lo"), chunks.map { chunk -> chunk.text })
        assertEquals(history, repository.lastHistory)
    }

    @Test
    fun invoke_onRepositoryFailure_flowThrows() = runTest {
        val repository = FakeStreamAiRepository(error = IllegalStateException("network down"))

        assertFailsWith<IllegalStateException> {
            SendMessageStreamUseCase(repository)
                .invoke(listOf(ChatMessageModel(author = MessageAuthor.USER, text = "hello")))
                .toList()
        }
    }
}

private class FakeStreamAiRepository(
    private val chunks: List<String> = emptyList(),
    private val error: Throwable? = null,
) : AiRepository {

    var lastHistory: List<ChatMessageModel>? = null
        private set

    override suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel =
        ChatMessageModel(author = MessageAuthor.ASSISTANT, text = chunks.joinToString(separator = ""))

    override fun sendMessageStream(history: List<ChatMessageModel>): Flow<ChatStreamChunkModel> = flow {
        lastHistory = history
        error?.let { failure -> throw failure }
        chunks.forEach { chunk -> emit(ChatStreamChunkModel(text = chunk)) }
    }
}
