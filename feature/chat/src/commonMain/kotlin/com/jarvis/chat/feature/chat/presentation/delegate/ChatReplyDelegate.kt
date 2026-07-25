package com.jarvis.chat.feature.chat.presentation.delegate

import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.AiException
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageStreamUseCase
import com.jarvis.chat.feature.chat.domain.mapper.toChatMessageModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import com.jarvis.chat.feature.chat.presentation.model.ChatEvent
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import kotlin.random.Random
import kotlin.time.Clock

private const val MESSAGE_ID_PREFIX = "msg-"

internal class ChatReplyDelegate(
    private val sendMessageStreamUseCase: SendMessageStreamUseCase,
    private val viewModelScope: CoroutineScope,
    private val currentState: () -> ChatState,
    private val updateState: (ChatState.() -> ChatState) -> Unit,
    private val postEvent: (ChatEvent) -> Unit,
    private val dispatch: (ChatAction) -> Unit,
    private val persistHistory: (List<HistoryMessageModel>) -> Unit,
) {

    private var replyJob: Job? = null
    private var activeAssistantMessageId: String? = null

    fun onSendClicked() {
        val text = currentState().inputText.trim()
        if (text.isEmpty() || currentState().isLoading) {
            return
        }
        val userMessage = createMessage(author = MessageAuthor.USER, text = text)
        val history = currentState().messages + userMessage
        updateState {
            copy(
                messages = history,
                inputText = "",
                isLoading = true,
                error = null,
                lastSentText = text,
            )
        }
        postEvent(ChatEvent.ScrollToBottom)
        persistHistory(history)
        requestReply(history)
    }

    fun onRetryClicked() {
        val text = currentState().lastSentText
        if (text.isEmpty() || currentState().isLoading) {
            return
        }
        updateState {
            copy(
                isLoading = true,
                error = null,
            )
        }
        requestReply(currentState().messages)
    }

    fun onStopClicked() {
        replyJob?.cancel()
        replyJob = null
        val pendingMessage = currentState().messages.find { message -> message.id == activeAssistantMessageId }
        activeAssistantMessageId = null
        val history = if (pendingMessage != null && pendingMessage.text.isEmpty()) {
            currentState().messages.withoutMessage(pendingMessage.id)
        } else {
            currentState().messages
        }
        updateState { copy(messages = history, isLoading = false, error = null) }
        if (pendingMessage != null && pendingMessage.text.isNotEmpty()) {
            persistHistory(history)
        }
    }

    fun onReplyChunkReceived(messageId: String, textChunk: String) {
        val history = currentState().messages.map { message ->
            if (message.id == messageId) message.copy(text = message.text + textChunk) else message
        }
        updateState { copy(messages = history) }
    }

    fun onReplyCompleted() {
        activeAssistantMessageId = null
        replyJob = null
        updateState { copy(isLoading = false, error = null) }
        postEvent(ChatEvent.ScrollToBottom)
        persistHistory(currentState().messages)
    }

    fun onReplyFailed(messageId: String, error: AiErrorModel) {
        activeAssistantMessageId = null
        replyJob = null
        val history = currentState().messages.withoutMessage(messageId)
        updateState {
            copy(
                messages = history,
                isLoading = false,
                error = error,
            )
        }
    }

    @Suppress("TooGenericExceptionCaught")
    private fun requestReply(history: List<HistoryMessageModel>) {
        replyJob?.cancel()
        val assistantMessage = createMessage(author = MessageAuthor.ASSISTANT, text = "")
        activeAssistantMessageId = assistantMessage.id
        updateState { copy(messages = history + assistantMessage) }
        replyJob = viewModelScope.launch {
            try {
                sendMessageStreamUseCase(history.map { message -> message.toChatMessageModel() })
                    .collect { textChunk ->
                        dispatch(ChatAction.Internal.ReplyChunkReceived(assistantMessage.id, textChunk))
                    }
                dispatch(ChatAction.Internal.ReplyCompleted)
            } catch (cancellation: CancellationException) {
                throw cancellation
            } catch (throwable: Throwable) {
                val error = (throwable as? AiException)?.error ?: AiErrorModel.Unknown
                dispatch(ChatAction.Internal.ReplyFailed(assistantMessage.id, error))
            }
        }
    }

    private fun createMessage(author: MessageAuthor, text: String): HistoryMessageModel =
        HistoryMessageModel(
            id = "$MESSAGE_ID_PREFIX${Random.nextLong()}",
            author = author,
            text = text,
            isFavorite = false,
            timestamp = Clock.System.now().toEpochMilliseconds(),
        )

    private fun List<HistoryMessageModel>.withoutMessage(messageId: String): List<HistoryMessageModel> =
        filterNot { message -> message.id == messageId }
}
