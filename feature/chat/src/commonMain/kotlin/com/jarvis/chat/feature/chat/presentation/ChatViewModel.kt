package com.jarvis.chat.feature.chat.presentation

import androidx.lifecycle.viewModelScope
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.AiException
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageStreamUseCase
import com.jarvis.chat.feature.chat.domain.mapper.toChatMessageModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.usecase.ClearChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ExportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ImportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.SaveChatHistoryUseCase
import com.jarvis.chat.feature.chat.presentation.mapper.ChatUiMapper
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import com.jarvis.chat.feature.chat.presentation.model.ChatEvent
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import com.jarvis.chat.feature.chat.presentation.model.ChatUiModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import kotlin.random.Random
import kotlin.time.Clock

private const val MESSAGE_ID_PREFIX = "msg-"
private const val EXPORT_MESSAGE_PREFIX = "History exported to "
private const val EXPORT_FAILED_MESSAGE = "Export failed. Please try again."
private const val IMPORT_FAILED_MESSAGE = "Import failed. Invalid file."
private const val IMPORT_MESSAGE_PREFIX = "Imported history: "
private const val IMPORT_MESSAGE_SUFFIX = " messages."
private const val COPIED_MESSAGE = "Скопировано"
private const val CLEAR_HISTORY_MESSAGE = "Chat history cleared."
private const val CLEAR_HISTORY_FAILED_MESSAGE = "Failed to clear history. Please try again."

internal class ChatViewModel(
    private val sendMessageStreamUseCase: SendMessageStreamUseCase,
    private val loadChatHistoryUseCase: LoadChatHistoryUseCase,
    private val saveChatHistoryUseCase: SaveChatHistoryUseCase,
    private val clearChatHistoryUseCase: ClearChatHistoryUseCase,
    private val exportChatHistoryUseCase: ExportChatHistoryUseCase,
    private val importChatHistoryUseCase: ImportChatHistoryUseCase,
    uiMapper: ChatUiMapper,
) : UdfBaseViewModel<ChatAction, ChatUiModel, ChatState, ChatEvent>(
    initialState = ChatState(),
    uiMapper = uiMapper,
) {

    private var replyJob: Job? = null
    private var activeAssistantMessageId: String? = null

    init {
        loadHistory()
    }

    override fun onAction(action: ChatAction) {
        when (action) {
            is ChatAction.Ui.InputChanged -> onInputChanged(action.text)
            is ChatAction.Ui.VoiceTranscribed -> onInputChanged(action.text)
            is ChatAction.Ui.SendClicked -> onSendClicked()
            is ChatAction.Ui.StopClicked -> onStopClicked()
            is ChatAction.Ui.SuggestionClicked -> onSuggestionClicked(action.text)
            is ChatAction.Ui.RetryClicked -> onRetryClicked()
            is ChatAction.Ui.FavoriteToggled -> onFavoriteToggled(action.messageId)
            is ChatAction.Ui.MessageCopied -> onMessageCopied()
            is ChatAction.Ui.FavoritesFilterToggled -> onFavoritesFilterToggled()
            is ChatAction.Ui.ExportClicked -> onExportClicked()
            is ChatAction.Ui.ImportRequested -> onImportRequested(action.json)
            is ChatAction.Ui.ClearHistoryClicked -> onClearHistoryClicked()
            is ChatAction.Ui.ClearHistoryConfirmed -> onClearHistoryConfirmed()
            is ChatAction.Ui.ClearHistoryCancelled -> onClearHistoryCancelled()
            is ChatAction.Internal.HistoryLoaded -> onHistoryLoaded(action.messages)
            is ChatAction.Internal.ReplyChunkReceived -> onReplyChunkReceived(action.messageId, action.textChunk)
            is ChatAction.Internal.ReplyCompleted -> onReplyCompleted()
            is ChatAction.Internal.ReplyFailed -> onReplyFailed(action.messageId, action.error)
            is ChatAction.Internal.Exported -> onExported(action.filePath)
            is ChatAction.Internal.ExportFailed -> onExportFailed()
            is ChatAction.Internal.Imported -> onImported(action.messages)
            is ChatAction.Internal.ImportFailed -> onImportFailed()
            is ChatAction.Internal.HistoryCleared -> onHistoryCleared()
            is ChatAction.Internal.ClearHistoryFailed -> onClearHistoryFailed()
        }
    }

    private fun onInputChanged(text: String) {
        updateState { copy(inputText = text) }
    }

    private fun onSendClicked() {
        val text = currentState.inputText.trim()
        if (text.isEmpty() || currentState.isLoading) {
            return
        }
        val userMessage = createMessage(author = MessageAuthor.USER, text = text)
        val history = currentState.messages + userMessage
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
        persist(history)
        requestReply(history)
    }

    private fun onSuggestionClicked(text: String) {
        onInputChanged(text)
        onSendClicked()
    }

    private fun onRetryClicked() {
        val text = currentState.lastSentText
        if (text.isEmpty() || currentState.isLoading) {
            return
        }
        updateState {
            copy(
                isLoading = true,
                error = null,
            )
        }
        requestReply(currentState.messages)
    }

    private fun onStopClicked() {
        replyJob?.cancel()
        replyJob = null
        val pendingMessage = currentState.messages.find { message -> message.id == activeAssistantMessageId }
        activeAssistantMessageId = null
        val history = if (pendingMessage != null && pendingMessage.text.isEmpty()) {
            currentState.messages.withoutMessage(pendingMessage.id)
        } else {
            currentState.messages
        }
        updateState { copy(messages = history, isLoading = false, error = null) }
        if (pendingMessage != null && pendingMessage.text.isNotEmpty()) {
            persist(history)
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
                        onAction(ChatAction.Internal.ReplyChunkReceived(assistantMessage.id, textChunk))
                    }
                onAction(ChatAction.Internal.ReplyCompleted)
            } catch (cancellation: CancellationException) {
                throw cancellation
            } catch (throwable: Throwable) {
                val error = (throwable as? AiException)?.error ?: AiErrorModel.Unknown
                onAction(ChatAction.Internal.ReplyFailed(assistantMessage.id, error))
            }
        }
    }

    private fun onReplyChunkReceived(messageId: String, textChunk: String) {
        val history = currentState.messages.map { message ->
            if (message.id == messageId) message.copy(text = message.text + textChunk) else message
        }
        updateState { copy(messages = history) }
    }

    private fun onReplyCompleted() {
        activeAssistantMessageId = null
        replyJob = null
        updateState { copy(isLoading = false, error = null) }
        postEvent(ChatEvent.ScrollToBottom)
        persist(currentState.messages)
    }

    private fun onReplyFailed(messageId: String, error: AiErrorModel) {
        activeAssistantMessageId = null
        replyJob = null
        val history = currentState.messages.withoutMessage(messageId)
        updateState {
            copy(
                messages = history,
                isLoading = false,
                error = error,
            )
        }
    }

    private fun onFavoriteToggled(messageId: String) {
        val history = currentState.messages.map { message ->
            if (message.id == messageId) message.copy(isFavorite = !message.isFavorite) else message
        }
        updateState { copy(messages = history) }
        persist(history)
    }

    private fun onMessageCopied() {
        postEvent(ChatEvent.ShowMessage(COPIED_MESSAGE))
    }

    private fun onFavoritesFilterToggled() {
        updateState { copy(isFavoritesFilterActive = !isFavoritesFilterActive) }
    }

    private fun onExportClicked() {
        viewModelScope.launch {
            exportChatHistoryUseCase(currentState.messages)
                .onSuccess { filePath -> onAction(ChatAction.Internal.Exported(filePath)) }
                .onFailure { onAction(ChatAction.Internal.ExportFailed) }
        }
    }

    private fun onExported(filePath: String) {
        postEvent(ChatEvent.ShowMessage("$EXPORT_MESSAGE_PREFIX$filePath"))
    }

    private fun onExportFailed() {
        postEvent(ChatEvent.ShowMessage(EXPORT_FAILED_MESSAGE))
    }

    private fun onImportRequested(json: String) {
        viewModelScope.launch {
            importChatHistoryUseCase(json = json, strategy = ImportStrategy.MERGE, current = currentState.messages)
                .onSuccess { messages -> onAction(ChatAction.Internal.Imported(messages)) }
                .onFailure { onAction(ChatAction.Internal.ImportFailed) }
        }
    }

    private fun onImported(messages: List<HistoryMessageModel>) {
        updateState { copy(messages = messages) }
        postEvent(ChatEvent.ShowMessage("$IMPORT_MESSAGE_PREFIX${messages.size}$IMPORT_MESSAGE_SUFFIX"))
        postEvent(ChatEvent.ScrollToBottom)
    }

    private fun onImportFailed() {
        postEvent(ChatEvent.ShowMessage(IMPORT_FAILED_MESSAGE))
    }

    private fun onClearHistoryClicked() {
        updateState { copy(showClearConfirmation = true) }
    }

    private fun onClearHistoryCancelled() {
        updateState { copy(showClearConfirmation = false) }
    }

    private fun onClearHistoryConfirmed() {
        updateState { copy(showClearConfirmation = false) }
        viewModelScope.launch {
            clearChatHistoryUseCase()
                .onSuccess { onAction(ChatAction.Internal.HistoryCleared) }
                .onFailure { onAction(ChatAction.Internal.ClearHistoryFailed) }
        }
    }

    private fun onHistoryCleared() {
        updateState {
            copy(
                messages = emptyList(),
                isFavoritesFilterActive = false,
                error = null,
                lastSentText = "",
            )
        }
        postEvent(ChatEvent.ShowMessage(CLEAR_HISTORY_MESSAGE))
    }

    private fun onClearHistoryFailed() {
        postEvent(ChatEvent.ShowMessage(CLEAR_HISTORY_FAILED_MESSAGE))
    }

    private fun loadHistory() {
        viewModelScope.launch {
            val messages = loadChatHistoryUseCase()
            onAction(ChatAction.Internal.HistoryLoaded(messages))
        }
    }

    private fun onHistoryLoaded(messages: List<HistoryMessageModel>) {
        updateState { copy(messages = messages) }
        postEvent(ChatEvent.ScrollToBottom)
    }

    private fun persist(messages: List<HistoryMessageModel>) {
        viewModelScope.launch {
            saveChatHistoryUseCase(messages)
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
