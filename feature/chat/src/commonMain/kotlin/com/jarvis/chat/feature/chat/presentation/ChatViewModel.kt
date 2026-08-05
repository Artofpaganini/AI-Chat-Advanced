package com.jarvis.chat.feature.chat.presentation

import androidx.lifecycle.viewModelScope
import com.jarvis.chat.core.micromodel.domain.usecase.ClassifyMessageUseCase
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigProvider
import com.jarvis.chat.feature.ai.domain.model.InferenceModeProvider
import com.jarvis.chat.feature.ai.domain.usecase.CheckInputGuardUseCase
import com.jarvis.chat.feature.ai.domain.usecase.CheckOutputGuardUseCase
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageStreamUseCase
import com.jarvis.chat.feature.ai.domain.usecase.SendMultiStageMessageUseCase
import com.jarvis.chat.feature.chat.domain.model.MicroModelGateSettingProvider
import com.jarvis.chat.feature.chat.domain.usecase.ClearChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.DeleteMessageUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ExportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ImportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatSessionsUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ObserveActiveChatSessionUseCase
import com.jarvis.chat.feature.chat.domain.usecase.SaveChatHistoryUseCase
import com.jarvis.chat.feature.chat.presentation.delegate.ChatExportImportDelegate
import com.jarvis.chat.feature.chat.presentation.delegate.ChatHistoryDelegate
import com.jarvis.chat.feature.chat.presentation.delegate.ChatReplyDelegate
import com.jarvis.chat.feature.chat.presentation.delegate.ChatSpeechDelegate
import com.jarvis.chat.feature.chat.presentation.mapper.ChatUiMapper
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import com.jarvis.chat.feature.chat.presentation.model.ChatEvent
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import com.jarvis.chat.feature.chat.presentation.model.ChatUiModel

private const val COPIED_MESSAGE = "Скопировано"

internal class ChatViewModel(
    sendMessageStreamUseCase: SendMessageStreamUseCase,
    classifyMessageUseCase: ClassifyMessageUseCase,
    microModelGateSettingProvider: MicroModelGateSettingProvider,
    sendMultiStageMessageUseCase: SendMultiStageMessageUseCase,
    inferenceModeProvider: InferenceModeProvider,
    aiProviderConfigProvider: AiProviderConfigProvider,
    checkInputGuardUseCase: CheckInputGuardUseCase,
    checkOutputGuardUseCase: CheckOutputGuardUseCase,
    loadChatSessionsUseCase: LoadChatSessionsUseCase,
    observeActiveChatSessionUseCase: ObserveActiveChatSessionUseCase,
    loadChatHistoryUseCase: LoadChatHistoryUseCase,
    saveChatHistoryUseCase: SaveChatHistoryUseCase,
    clearChatHistoryUseCase: ClearChatHistoryUseCase,
    deleteMessageUseCase: DeleteMessageUseCase,
    exportChatHistoryUseCase: ExportChatHistoryUseCase,
    importChatHistoryUseCase: ImportChatHistoryUseCase,
    uiMapper: ChatUiMapper,
) : UdfBaseViewModel<ChatAction, ChatUiModel, ChatState, ChatEvent>(
    initialState = ChatState(),
    uiMapper = uiMapper,
) {

    private val replyDelegate = ChatReplyDelegate(
        sendMessageStreamUseCase = sendMessageStreamUseCase,
        classifyMessageUseCase = classifyMessageUseCase,
        microModelGateSettingProvider = microModelGateSettingProvider,
        sendMultiStageMessageUseCase = sendMultiStageMessageUseCase,
        inferenceModeProvider = inferenceModeProvider,
        aiProviderConfigProvider = aiProviderConfigProvider,
        checkInputGuardUseCase = checkInputGuardUseCase,
        checkOutputGuardUseCase = checkOutputGuardUseCase,
        saveChatHistoryUseCase = saveChatHistoryUseCase,
        viewModelScope = viewModelScope,
        currentState = ::currentState,
        updateState = ::updateState,
        postEvent = ::postEvent,
        dispatch = ::onAction,
    )

    private val historyDelegate = ChatHistoryDelegate(
        loadChatSessionsUseCase = loadChatSessionsUseCase,
        observeActiveChatSessionUseCase = observeActiveChatSessionUseCase,
        loadChatHistoryUseCase = loadChatHistoryUseCase,
        saveChatHistoryUseCase = saveChatHistoryUseCase,
        clearChatHistoryUseCase = clearChatHistoryUseCase,
        deleteMessageUseCase = deleteMessageUseCase,
        viewModelScope = viewModelScope,
        currentState = ::currentState,
        updateState = ::updateState,
        postEvent = ::postEvent,
        dispatch = ::onAction,
        liveSessionMessages = replyDelegate::liveMessagesOrNull,
        isSessionGenerating = replyDelegate::isGenerating,
    )

    private val exportImportDelegate = ChatExportImportDelegate(
        exportChatHistoryUseCase = exportChatHistoryUseCase,
        importChatHistoryUseCase = importChatHistoryUseCase,
        viewModelScope = viewModelScope,
        currentState = ::currentState,
        updateState = ::updateState,
        postEvent = ::postEvent,
        dispatch = ::onAction,
    )

    private val speechDelegate = ChatSpeechDelegate(
        currentState = ::currentState,
        updateState = ::updateState,
    )

    init {
        historyDelegate.start()
    }

    override fun onAction(action: ChatAction) {
        when (action) {
            is ChatAction.Ui.InputChanged -> onInputChanged(action.text)
            is ChatAction.Ui.VoiceTranscribed -> onInputChanged(action.text)
            is ChatAction.Ui.SendClicked -> replyDelegate.onSendClicked()
            is ChatAction.Ui.StopClicked -> replyDelegate.onStopClicked()
            is ChatAction.Ui.SuggestionClicked -> onSuggestionClicked(action.text)
            is ChatAction.Ui.RetryClicked -> replyDelegate.onRetryClicked()
            is ChatAction.Ui.FavoriteToggled -> onFavoriteToggled(action.messageId)
            is ChatAction.Ui.SpeakToggled -> speechDelegate.onSpeakToggled(action.messageId)
            is ChatAction.Ui.SpeechFinished -> speechDelegate.onSpeechFinished(action.messageId)
            is ChatAction.Ui.MessageCopied -> onMessageCopied()
            is ChatAction.Ui.FavoritesFilterToggled -> onFavoritesFilterToggled()
            is ChatAction.Ui.ExportClicked -> exportImportDelegate.onExportClicked()
            is ChatAction.Ui.ImportRequested -> exportImportDelegate.onImportRequested(action.json)
            is ChatAction.Ui.ClearHistoryClicked -> historyDelegate.onClearHistoryClicked()
            is ChatAction.Ui.ClearHistoryConfirmed -> historyDelegate.onClearHistoryConfirmed()
            is ChatAction.Ui.ClearHistoryCancelled -> historyDelegate.onClearHistoryCancelled()
            is ChatAction.Ui.DeleteMessageClicked -> historyDelegate.onDeleteMessageClicked(action.messageId)
            is ChatAction.Ui.DeleteMessageConfirmed -> historyDelegate.onDeleteMessageConfirmed()
            is ChatAction.Ui.DeleteMessageCancelled -> historyDelegate.onDeleteMessageCancelled()
            is ChatAction.Internal.ActiveSessionChanged -> historyDelegate.onActiveSessionChanged(action.sessionId)
            is ChatAction.Internal.HistoryLoaded -> historyDelegate.onHistoryLoaded(action.sessionId, action.messages)
            is ChatAction.Internal.ReplyChunkReceived ->
                replyDelegate.onReplyChunkReceived(
                    sessionId = action.sessionId,
                    messageId = action.messageId,
                    textChunk = action.textChunk,
                    modelId = action.modelId,
                    triage = action.triage,
                    routeDecision = action.routeDecision,
                    multiStage = action.multiStage,
                    gatewaySignal = action.gatewaySignal,
                    gatewayOutputTruncation = action.gatewayOutputTruncation,
                )
            is ChatAction.Internal.ReplyCompleted -> replyDelegate.onReplyCompleted(action.sessionId)
            is ChatAction.Internal.ReplyFailed -> replyDelegate.onReplyFailed(action.sessionId, action.messageId, action.error)
            is ChatAction.Internal.Exported -> exportImportDelegate.onExported(action.filePath)
            is ChatAction.Internal.ExportFailed -> exportImportDelegate.onExportFailed()
            is ChatAction.Internal.Imported -> exportImportDelegate.onImported(action.outcome)
            is ChatAction.Internal.ImportFailed -> exportImportDelegate.onImportFailed()
            is ChatAction.Internal.HistoryCleared -> historyDelegate.onHistoryCleared()
            is ChatAction.Internal.ClearHistoryFailed -> historyDelegate.onClearHistoryFailed()
            is ChatAction.Internal.MessageDeleted -> historyDelegate.onMessageDeleted(action.messages)
            is ChatAction.Internal.DeleteMessageFailed -> historyDelegate.onDeleteMessageFailed()
        }
    }

    private fun onInputChanged(text: String) {
        updateState { copy(inputText = text) }
    }

    private fun onSuggestionClicked(text: String) {
        onInputChanged(text)
        replyDelegate.onSendClicked()
    }

    private fun onFavoriteToggled(messageId: String) {
        val history = currentState.messages.map { message ->
            if (message.id == messageId) message.copy(isFavorite = !message.isFavorite) else message
        }
        updateState { copy(messages = history) }
        historyDelegate.persist(currentState.activeSessionId, history)
    }

    private fun onMessageCopied() {
        postEvent(ChatEvent.ShowMessage(COPIED_MESSAGE))
    }

    private fun onFavoritesFilterToggled() {
        updateState { copy(isFavoritesFilterActive = !isFavoritesFilterActive) }
    }
}
