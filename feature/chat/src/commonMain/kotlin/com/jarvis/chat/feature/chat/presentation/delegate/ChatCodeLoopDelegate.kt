package com.jarvis.chat.feature.chat.presentation.delegate

import com.jarvis.chat.feature.ai.di.CodeLoopDefaults
import com.jarvis.chat.feature.ai.domain.mapper.toCodeLoopRunModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopErrorModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopException
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageEventModel
import com.jarvis.chat.feature.ai.domain.usecase.RunCodeLoopUseCase
import com.jarvis.chat.feature.chat.domain.mapper.toReplyText
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import kotlinx.coroutines.CancellationException

internal class ChatCodeLoopDelegate(
    private val runCodeLoopUseCase: RunCodeLoopUseCase,
    private val dispatch: (ChatAction) -> Unit,
) {

    @Suppress("TooGenericExceptionCaught")
    suspend fun requestReply(sessionId: String, messageId: String, history: List<HistoryMessageModel>) {
        val task = history.lastOrNull()?.text.orEmpty()
        val collectedEvents = mutableListOf<CodeLoopStageEventModel>()
        var isFinalTextSent = false
        try {
            runCodeLoopUseCase(task = task, maxIterations = CodeLoopDefaults.MAX_ITERATIONS)
                .collect { event ->
                    collectedEvents += event
                    isFinalTextSent = dispatchProgress(
                        sessionId = sessionId,
                        messageId = messageId,
                        task = task,
                        collectedEvents = collectedEvents,
                        isFinalTextSent = isFinalTextSent,
                    )
                }
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (throwable: Throwable) {
            val error = (throwable as? CodeLoopException)?.error
                ?: CodeLoopErrorModel.MalformedResponse(detail = throwable.message.orEmpty())
            dispatchProgress(
                sessionId = sessionId,
                messageId = messageId,
                task = task,
                collectedEvents = collectedEvents,
                isFinalTextSent = isFinalTextSent,
                error = error,
            )
        }
        dispatch(ChatAction.Internal.ReplyCompleted(sessionId))
    }

    private fun dispatchProgress(
        sessionId: String,
        messageId: String,
        task: String,
        collectedEvents: List<CodeLoopStageEventModel>,
        isFinalTextSent: Boolean,
        error: CodeLoopErrorModel? = null,
    ): Boolean {
        val runModel = collectedEvents.toCodeLoopRunModel(task = task, error = error)
        val shouldSendFinalText = !runModel.isRunning && !isFinalTextSent
        val textChunk = if (shouldSendFinalText) runModel.toReplyText() else ""
        dispatch(
            ChatAction.Internal.ReplyChunkReceived(
                sessionId = sessionId,
                messageId = messageId,
                textChunk = textChunk,
                modelId = null,
                triage = null,
                codeLoop = runModel,
            ),
        )
        return isFinalTextSent || shouldSendFinalText
    }
}
