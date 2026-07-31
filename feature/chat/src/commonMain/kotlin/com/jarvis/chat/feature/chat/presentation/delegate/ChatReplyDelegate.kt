package com.jarvis.chat.feature.chat.presentation.delegate

import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.AiException
import com.jarvis.chat.feature.ai.domain.model.InferenceModeModel
import com.jarvis.chat.feature.ai.domain.model.InferenceModeProvider
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.model.MultiStageResultModel
import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageStreamUseCase
import com.jarvis.chat.feature.ai.domain.usecase.SendMultiStageMessageUseCase
import com.jarvis.chat.feature.chat.domain.mapper.toRequestContext
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.usecase.SaveChatHistoryUseCase
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
    private val sendMultiStageMessageUseCase: SendMultiStageMessageUseCase,
    private val inferenceModeProvider: InferenceModeProvider,
    private val saveChatHistoryUseCase: SaveChatHistoryUseCase,
    private val viewModelScope: CoroutineScope,
    private val currentState: () -> ChatState,
    private val updateState: (ChatState.() -> ChatState) -> Unit,
    private val postEvent: (ChatEvent) -> Unit,
    private val dispatch: (ChatAction) -> Unit,
) {

    private val replyJobs = mutableMapOf<String, Job>()
    private val replyBuffers = mutableMapOf<String, List<HistoryMessageModel>>()
    private val activeAssistantMessageIds = mutableMapOf<String, String>()

    fun liveMessagesOrNull(sessionId: String): List<HistoryMessageModel>? = replyBuffers[sessionId]

    fun isGenerating(sessionId: String): Boolean = replyJobs.containsKey(sessionId)

    fun onSendClicked() {
        val sessionId = currentState().activeSessionId
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
        persist(sessionId, history)
        requestReply(sessionId, history)
    }

    fun onRetryClicked() {
        val sessionId = currentState().activeSessionId
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
        requestReply(sessionId, currentState().messages)
    }

    fun onStopClicked() {
        val sessionId = currentState().activeSessionId
        replyJobs.remove(sessionId)?.cancel()
        val messageId = activeAssistantMessageIds.remove(sessionId)
        replyBuffers.remove(sessionId)
        val pendingMessage = messageId?.let { id -> currentState().messages.find { message -> message.id == id } }
        val history = if (pendingMessage != null && pendingMessage.text.isEmpty()) {
            currentState().messages.withoutMessage(pendingMessage.id)
        } else {
            currentState().messages
        }
        updateState { copy(messages = history, isLoading = false, error = null) }
        if (pendingMessage != null && pendingMessage.text.isNotEmpty()) {
            persist(sessionId, history)
        }
    }

    fun onReplyChunkReceived(
        sessionId: String,
        messageId: String,
        textChunk: String,
        modelId: String?,
        triage: TriageModel?,
        multiStage: MultiStageResultModel? = null,
    ) {
        val buffer = replyBuffers[sessionId] ?: return
        val updatedBuffer = buffer.map { message ->
            if (message.id == messageId) {
                message.copy(
                    text = message.text + textChunk,
                    modelId = modelId ?: message.modelId,
                    triage = triage ?: message.triage,
                    multiStage = multiStage ?: message.multiStage,
                )
            } else {
                message
            }
        }
        replyBuffers[sessionId] = updatedBuffer
        if (sessionId == currentState().activeSessionId) {
            updateState { copy(messages = updatedBuffer) }
        }
    }

    fun onReplyCompleted(sessionId: String) {
        replyJobs.remove(sessionId)
        activeAssistantMessageIds.remove(sessionId)
        val finalMessages = replyBuffers.remove(sessionId) ?: return
        if (sessionId == currentState().activeSessionId) {
            updateState { copy(isLoading = false, error = null) }
            postEvent(ChatEvent.ScrollToBottom)
        }
        persist(sessionId, finalMessages)
    }

    fun onReplyFailed(sessionId: String, messageId: String, error: AiErrorModel) {
        replyJobs.remove(sessionId)
        activeAssistantMessageIds.remove(sessionId)
        replyBuffers.remove(sessionId)
        if (sessionId == currentState().activeSessionId) {
            val history = currentState().messages.withoutMessage(messageId)
            updateState {
                copy(
                    messages = history,
                    isLoading = false,
                    error = error,
                )
            }
        }
    }

    private fun requestReply(sessionId: String, history: List<HistoryMessageModel>) {
        replyJobs.remove(sessionId)?.cancel()
        val assistantMessage = createMessage(author = MessageAuthor.ASSISTANT, text = "")
        activeAssistantMessageIds[sessionId] = assistantMessage.id
        val fullHistory = history + assistantMessage
        replyBuffers[sessionId] = fullHistory
        if (sessionId == currentState().activeSessionId) {
            updateState { copy(messages = fullHistory) }
        }
        replyJobs[sessionId] = viewModelScope.launch {
            when (inferenceModeProvider.currentMode()) {
                InferenceModeModel.ONE_SHOT -> requestStreamReply(sessionId, assistantMessage.id, history)
                InferenceModeModel.MULTI_STAGE -> requestMultiStageReply(sessionId, assistantMessage.id, history)
            }
        }
    }

    @Suppress("TooGenericExceptionCaught")
    private suspend fun requestStreamReply(sessionId: String, messageId: String, history: List<HistoryMessageModel>) {
        try {
            sendMessageStreamUseCase(history.toRequestContext())
                .collect { chunk ->
                    dispatch(
                        ChatAction.Internal.ReplyChunkReceived(
                            sessionId = sessionId,
                            messageId = messageId,
                            textChunk = chunk.text,
                            modelId = chunk.modelId,
                            triage = chunk.triage,
                        ),
                    )
                }
            dispatch(ChatAction.Internal.ReplyCompleted(sessionId))
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (throwable: Throwable) {
            val error = (throwable as? AiException)?.error ?: AiErrorModel.Unknown
            dispatch(ChatAction.Internal.ReplyFailed(sessionId, messageId, error))
        }
    }

    @Suppress("TooGenericExceptionCaught")
    private suspend fun requestMultiStageReply(sessionId: String, messageId: String, history: List<HistoryMessageModel>) {
        try {
            val caseText = history.lastOrNull()?.text.orEmpty()
            val result = sendMultiStageMessageUseCase(caseText)
            dispatch(
                ChatAction.Internal.ReplyChunkReceived(
                    sessionId = sessionId,
                    messageId = messageId,
                    textChunk = result.answerText,
                    modelId = null,
                    triage = null,
                    multiStage = result,
                ),
            )
            dispatch(ChatAction.Internal.ReplyCompleted(sessionId))
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (throwable: Throwable) {
            val error = (throwable as? AiException)?.error ?: AiErrorModel.Unknown
            dispatch(ChatAction.Internal.ReplyFailed(sessionId, messageId, error))
        }
    }

    private fun persist(sessionId: String, messages: List<HistoryMessageModel>) {
        viewModelScope.launch {
            saveChatHistoryUseCase(sessionId, messages)
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
