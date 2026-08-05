package com.jarvis.chat.feature.chat.presentation.delegate

import com.jarvis.chat.core.micromodel.domain.model.MicroTriageModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageRouteModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageStatusModel
import com.jarvis.chat.core.micromodel.domain.usecase.ClassifyMessageUseCase
import com.jarvis.chat.feature.ai.di.DeepSeekDefaults
import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.AiException
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigProvider
import com.jarvis.chat.feature.ai.domain.model.GatewayOutputTruncationModel
import com.jarvis.chat.feature.ai.domain.model.GatewaySignalModel
import com.jarvis.chat.feature.ai.domain.model.GuardTargetModel
import com.jarvis.chat.feature.ai.domain.model.InferenceModeModel
import com.jarvis.chat.feature.ai.domain.model.InferenceModeProvider
import com.jarvis.chat.feature.ai.domain.model.InputGuardResultModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.model.MultiStageResultModel
import com.jarvis.chat.feature.ai.domain.model.OutputGuardResultModel
import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.ai.domain.usecase.CheckInputGuardUseCase
import com.jarvis.chat.feature.ai.domain.usecase.CheckOutputGuardUseCase
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageStreamUseCase
import com.jarvis.chat.feature.ai.domain.usecase.SendMultiStageMessageUseCase
import com.jarvis.chat.feature.chat.domain.mapper.extractRouteFromAnswerText
import com.jarvis.chat.feature.chat.domain.mapper.mergeRouteWithMicroRoute
import com.jarvis.chat.feature.chat.domain.mapper.mergeWithMicroRoute
import com.jarvis.chat.feature.chat.domain.mapper.toFallbackTriageModel
import com.jarvis.chat.feature.chat.domain.mapper.toLocalReplyText
import com.jarvis.chat.feature.chat.domain.mapper.toRequestContext
import com.jarvis.chat.feature.chat.domain.mapper.toTextEstimatedTriageModel
import com.jarvis.chat.feature.chat.domain.mapper.toTriageModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.MicroModelGateSettingProvider
import com.jarvis.chat.feature.chat.domain.model.RouteDecisionModel
import com.jarvis.chat.feature.chat.domain.model.RouteSourceModel
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
    private val classifyMessageUseCase: ClassifyMessageUseCase,
    private val microModelGateSettingProvider: MicroModelGateSettingProvider,
    private val sendMultiStageMessageUseCase: SendMultiStageMessageUseCase,
    private val inferenceModeProvider: InferenceModeProvider,
    private val aiProviderConfigProvider: AiProviderConfigProvider,
    private val checkInputGuardUseCase: CheckInputGuardUseCase,
    private val checkOutputGuardUseCase: CheckOutputGuardUseCase,
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
    private val guardTargets = mutableMapOf<String, GuardTargetModel>()

    fun liveMessagesOrNull(sessionId: String): List<HistoryMessageModel>? = replyBuffers[sessionId]

    fun isGenerating(sessionId: String): Boolean = replyJobs.containsKey(sessionId)

    fun onSendClicked() {
        val sessionId = currentState().activeSessionId
        val text = currentState().inputText.trim()
        if (text.isEmpty() || currentState().isLoading) {
            return
        }
        val userMessage = createMessage(author = MessageAuthor.USER, text = text)
        val guardResult = checkInputGuardUseCase(text)
        if (guardResult is InputGuardResultModel.Blocked) {
            val guardMessage = createMessage(author = MessageAuthor.ASSISTANT, text = guardResult.reason)
                .copy(inputGuardBlocked = true)
            val history = currentState().messages + userMessage + guardMessage
            updateState {
                copy(
                    messages = history,
                    inputText = "",
                    error = null,
                    lastSentText = text,
                    blockedInputCount = blockedInputCount + 1,
                )
            }
            postEvent(ChatEvent.ScrollToBottom)
            persist(sessionId, history)
            return
        }
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
        guardTargets.remove(sessionId)
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
        routeDecision: RouteDecisionModel? = null,
        multiStage: MultiStageResultModel? = null,
        gatewaySignal: GatewaySignalModel? = null,
        gatewayOutputTruncation: GatewayOutputTruncationModel? = null,
    ) {
        val buffer = replyBuffers[sessionId] ?: return
        val updatedBuffer = buffer.map { message ->
            if (message.id == messageId) {
                message.copy(
                    text = message.text + textChunk,
                    modelId = modelId ?: message.modelId,
                    triage = triage ?: message.triage,
                    routeDecision = routeDecision ?: message.routeDecision,
                    multiStage = multiStage ?: message.multiStage,
                    gatewaySignal = gatewaySignal ?: message.gatewaySignal,
                    gatewayOutputTruncation = gatewayOutputTruncation ?: message.gatewayOutputTruncation,
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
        val assistantMessageId = activeAssistantMessageIds.remove(sessionId)
        val guardTarget = guardTargets.remove(sessionId) ?: GuardTargetModel.JARVIS
        val bufferedMessages = replyBuffers.remove(sessionId) ?: return
        val finalMessages = bufferedMessages.applyOutputGuardIfNeeded(assistantMessageId, guardTarget)
        if (sessionId == currentState().activeSessionId) {
            updateState { copy(isLoading = false, error = null, messages = finalMessages) }
            postEvent(ChatEvent.ScrollToBottom)
        }
        persist(sessionId, finalMessages)
    }

    private fun List<HistoryMessageModel>.applyOutputGuardIfNeeded(
        assistantMessageId: String?,
        target: GuardTargetModel,
    ): List<HistoryMessageModel> {
        val guardResult = find { message -> message.id == assistantMessageId }
            ?.takeIf { message -> message.text.isNotBlank() }
            ?.let { message -> checkOutputGuardUseCase(message.text, target) }
        if (guardResult !is OutputGuardResultModel.Blocked) {
            return this
        }
        updateState { copy(blockedOutputCount = blockedOutputCount + 1) }
        return map { message ->
            if (message.id == assistantMessageId) {
                message.copy(text = guardResult.fallbackMessage, outputGuardReasons = guardResult.reasons)
            } else {
                message
            }
        }
    }

    fun onReplyFailed(sessionId: String, messageId: String, error: AiErrorModel) {
        replyJobs.remove(sessionId)
        activeAssistantMessageIds.remove(sessionId)
        replyBuffers.remove(sessionId)
        guardTargets.remove(sessionId)
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

    @Suppress("TooGenericExceptionCaught")
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
            try {
                val userText = history.lastOrNull { message -> message.author == MessageAuthor.USER }?.text.orEmpty()
                val microResult = if (microModelGateSettingProvider.isMicroModelFirstEnabled()) {
                    classifyMessageUseCase(userText)
                } else {
                    null
                }
                val localMicroResult = microResult?.takeIf { result -> result.status == MicroTriageStatusModel.OK }
                guardTargets[sessionId] = currentGuardTarget(isLocalMicroReply = localMicroResult != null)
                updateState {
                    copy(
                        totalRoutedCount = totalRoutedCount + 1,
                        localHandledCount = if (localMicroResult != null) localHandledCount + 1 else localHandledCount,
                    )
                }
                if (localMicroResult != null) {
                    replyLocally(sessionId, assistantMessage.id, localMicroResult)
                } else {
                    when (inferenceModeProvider.currentMode()) {
                        InferenceModeModel.ONE_SHOT -> requestStreamReply(sessionId, assistantMessage.id, history, microResult)
                        InferenceModeModel.MULTI_STAGE -> requestMultiStageReply(sessionId, assistantMessage.id, history, microResult)
                    }
                }
            } catch (cancellation: CancellationException) {
                throw cancellation
            } catch (throwable: Throwable) {
                val error = (throwable as? AiException)?.error ?: AiErrorModel.Unknown
                dispatch(ChatAction.Internal.ReplyFailed(sessionId, assistantMessage.id, error))
            }
        }
    }

    private fun replyLocally(sessionId: String, messageId: String, microResult: MicroTriageModel) {
        dispatch(
            ChatAction.Internal.ReplyChunkReceived(
                sessionId = sessionId,
                messageId = messageId,
                textChunk = microResult.route.toLocalReplyText(),
                modelId = null,
                triage = microResult.toTriageModel(),
                routeDecision = RouteDecisionModel(
                    source = RouteSourceModel.LOCAL,
                    microRoute = microResult.route,
                    microConfidence = microResult.confidence,
                    elapsedMillis = microResult.elapsedMillis,
                ),
            ),
        )
        dispatch(ChatAction.Internal.ReplyCompleted(sessionId))
    }

    private suspend fun requestStreamReply(
        sessionId: String,
        messageId: String,
        history: List<HistoryMessageModel>,
        microResult: MicroTriageModel?,
    ) {
        val baseRouteDecision = microResult?.let { result ->
            RouteDecisionModel(
                source = RouteSourceModel.CLOUD,
                microRoute = result.route,
                microConfidence = result.confidence,
                elapsedMillis = result.elapsedMillis,
            )
        }
        sendMessageStreamUseCase(history.toRequestContext())
            .collect { chunk ->
                val llmTriage = chunk.triage
                val mergedTriage = llmTriage?.mergeWithMicroRoute(microResult?.route)
                val mergedRouteDecision = if (llmTriage != null && baseRouteDecision != null) {
                    baseRouteDecision.copy(llmRouteBeforeMerge = llmTriage.route)
                } else {
                    baseRouteDecision
                }
                dispatch(
                    ChatAction.Internal.ReplyChunkReceived(
                        sessionId = sessionId,
                        messageId = messageId,
                        textChunk = chunk.text,
                        modelId = chunk.modelId,
                        triage = mergedTriage,
                        routeDecision = mergedRouteDecision,
                        gatewaySignal = chunk.gatewaySignal,
                        gatewayOutputTruncation = chunk.outputTruncation,
                    ),
                )
            }
        applyPostStreamVerdict(sessionId, messageId, microResult)
        dispatch(ChatAction.Internal.ReplyCompleted(sessionId))
    }

    private suspend fun requestMultiStageReply(
        sessionId: String,
        messageId: String,
        history: List<HistoryMessageModel>,
        microResult: MicroTriageModel?,
    ) {
        val caseText = history.lastOrNull()?.text.orEmpty()
        val chainResult = sendMultiStageMessageUseCase(caseText)
        val mergedRoute = chainResult.route.mergeRouteWithMicroRoute(microResult?.route)
        val mergedResult = chainResult.copy(route = mergedRoute)
        val routeDecision = microResult?.let { result ->
            RouteDecisionModel(
                source = RouteSourceModel.CLOUD,
                microRoute = result.route,
                microConfidence = result.confidence,
                elapsedMillis = result.elapsedMillis,
                llmRouteBeforeMerge = chainResult.route,
            )
        }
        dispatch(
            ChatAction.Internal.ReplyChunkReceived(
                sessionId = sessionId,
                messageId = messageId,
                textChunk = mergedResult.answerText,
                modelId = null,
                triage = null,
                routeDecision = routeDecision,
                multiStage = mergedResult,
            ),
        )
        dispatch(ChatAction.Internal.ReplyCompleted(sessionId))
    }

    private fun applyPostStreamVerdict(sessionId: String, messageId: String, microResult: MicroTriageModel?) {
        val bufferedMessage = replyBuffers[sessionId]?.find { message -> message.id == messageId } ?: return
        if (bufferedMessage.triage != null) {
            return
        }
        val extractedRoute = bufferedMessage.text.extractRouteFromAnswerText()
        if (extractedRoute != null) {
            val mergedRoute = extractedRoute.mergeRouteWithMicroRoute(microResult?.route) ?: extractedRoute
            dispatch(
                ChatAction.Internal.ReplyChunkReceived(
                    sessionId = sessionId,
                    messageId = messageId,
                    textChunk = "",
                    modelId = null,
                    triage = mergedRoute.toTextEstimatedTriageModel(),
                ),
            )
            return
        }
        ensureEmergencyVisible(sessionId, messageId, microResult)
    }

    private fun ensureEmergencyVisible(sessionId: String, messageId: String, microResult: MicroTriageModel?) {
        if (microResult == null || microResult.route != MicroTriageRouteModel.EMERGENCY) {
            return
        }
        val currentTriage = replyBuffers[sessionId]?.find { message -> message.id == messageId }?.triage
        if (currentTriage != null) {
            return
        }
        dispatch(
            ChatAction.Internal.ReplyChunkReceived(
                sessionId = sessionId,
                messageId = messageId,
                textChunk = "",
                modelId = null,
                triage = microResult.toFallbackTriageModel(),
                routeDecision = RouteDecisionModel(
                    source = RouteSourceModel.CLOUD,
                    microRoute = microResult.route,
                    microConfidence = microResult.confidence,
                    elapsedMillis = microResult.elapsedMillis,
                ),
            ),
        )
    }

    private fun currentGuardTarget(isLocalMicroReply: Boolean): GuardTargetModel =
        when {
            isLocalMicroReply -> GuardTargetModel.ALVA
            inferenceModeProvider.currentMode() == InferenceModeModel.MULTI_STAGE -> GuardTargetModel.ALVA
            aiProviderConfigProvider.currentConfig().systemPrompt == DeepSeekDefaults.LOCAL_SYSTEM_PROMPT -> GuardTargetModel.ALVA
            else -> GuardTargetModel.JARVIS
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
