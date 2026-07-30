package com.jarvis.chat.feature.chat.presentation.delegate

import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.usecase.ExportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ImportChatHistoryUseCase
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import com.jarvis.chat.feature.chat.presentation.model.ChatEvent
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

private const val EXPORT_MESSAGE_PREFIX = "History exported to "
private const val EXPORT_FAILED_MESSAGE = "Export failed. Please try again."
private const val IMPORT_FAILED_MESSAGE = "Import failed. Invalid file."
private const val IMPORT_MESSAGE_PREFIX = "Imported history: "
private const val IMPORT_MESSAGE_SUFFIX = " messages."

internal class ChatExportImportDelegate(
    private val exportChatHistoryUseCase: ExportChatHistoryUseCase,
    private val importChatHistoryUseCase: ImportChatHistoryUseCase,
    private val viewModelScope: CoroutineScope,
    private val currentState: () -> ChatState,
    private val updateState: (ChatState.() -> ChatState) -> Unit,
    private val postEvent: (ChatEvent) -> Unit,
    private val dispatch: (ChatAction) -> Unit,
) {

    fun onExportClicked() {
        viewModelScope.launch {
            exportChatHistoryUseCase(currentState().messages)
                .onSuccess { filePath -> dispatch(ChatAction.Internal.Exported(filePath)) }
                .onFailure { dispatch(ChatAction.Internal.ExportFailed) }
        }
    }

    fun onExported(filePath: String) {
        postEvent(ChatEvent.ShowMessage("$EXPORT_MESSAGE_PREFIX$filePath"))
    }

    fun onExportFailed() {
        postEvent(ChatEvent.ShowMessage(EXPORT_FAILED_MESSAGE))
    }

    fun onImportRequested(json: String) {
        val sessionId = currentState().activeSessionId
        viewModelScope.launch {
            importChatHistoryUseCase(
                sessionId = sessionId,
                json = json,
                strategy = ImportStrategy.MERGE,
                current = currentState().messages,
            )
                .onSuccess { messages -> dispatch(ChatAction.Internal.Imported(messages)) }
                .onFailure { dispatch(ChatAction.Internal.ImportFailed) }
        }
    }

    fun onImported(messages: List<HistoryMessageModel>) {
        updateState { copy(messages = messages) }
        postEvent(ChatEvent.ShowMessage("$IMPORT_MESSAGE_PREFIX${messages.size}$IMPORT_MESSAGE_SUFFIX"))
        postEvent(ChatEvent.ScrollToBottom)
    }

    fun onImportFailed() {
        postEvent(ChatEvent.ShowMessage(IMPORT_FAILED_MESSAGE))
    }
}
