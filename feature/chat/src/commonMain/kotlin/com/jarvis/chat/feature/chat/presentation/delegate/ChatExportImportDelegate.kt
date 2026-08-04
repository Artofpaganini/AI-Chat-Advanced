package com.jarvis.chat.feature.chat.presentation.delegate

import com.jarvis.chat.feature.chat.domain.model.ImportOutcomeModel
import com.jarvis.chat.feature.chat.domain.model.ImportRejectionReasonModel
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
private const val IMPORT_FILE_REJECTED_PREFIX = "Import blocked: "
private const val IMPORT_DROPPED_PREFIX = " Dropped "
private const val IMPORT_DROPPED_SUFFIX = " suspicious message(s): "
private const val IMPORT_TRUNCATED_PREFIX = " Truncated "
private const val IMPORT_TRUNCATED_SUFFIX = " oversized message(s)."
private const val IMPORT_UNVERIFIED_PREFIX = " Warning: "
private const val IMPORT_UNVERIFIED_SUFFIX =
    " message(s) claim to be from the assistant but came from the file - not actual model output."
private const val REASON_FILE_TOO_LARGE = "the file is too large"
private const val REASON_TOO_MANY_MESSAGES = "the file has too many messages"
private const val REASON_HIDDEN_MARKUP = "hidden markup"
private const val REASON_DENSE_INVISIBLE_CHARS = "hidden invisible characters"
private const val REASON_INPUT_GUARD_BLOCKED = "an injection attempt"

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
                .onSuccess { outcome -> dispatch(ChatAction.Internal.Imported(outcome)) }
                .onFailure { dispatch(ChatAction.Internal.ImportFailed) }
        }
    }

    fun onImported(outcome: ImportOutcomeModel) {
        if (outcome.fileRejected) {
            val reason = outcome.fileRejectionReason?.toLabel().orEmpty()
            postEvent(ChatEvent.ShowMessage("$IMPORT_FILE_REJECTED_PREFIX$reason"))
            return
        }
        updateState { copy(messages = outcome.messages) }
        postEvent(ChatEvent.ShowMessage(outcome.toSummaryMessage()))
        postEvent(ChatEvent.ScrollToBottom)
    }

    fun onImportFailed() {
        postEvent(ChatEvent.ShowMessage(IMPORT_FAILED_MESSAGE))
    }
}

private fun ImportOutcomeModel.toSummaryMessage(): String {
    val summary = StringBuilder("$IMPORT_MESSAGE_PREFIX$acceptedCount$IMPORT_MESSAGE_SUFFIX")
    if (unverifiedAssistantCount > 0) {
        summary.append("$IMPORT_UNVERIFIED_PREFIX$unverifiedAssistantCount$IMPORT_UNVERIFIED_SUFFIX")
    }
    if (droppedCount > 0) {
        val reasons = dropReasons.joinToString(", ") { reason -> reason.toLabel() }
        summary.append("$IMPORT_DROPPED_PREFIX$droppedCount$IMPORT_DROPPED_SUFFIX$reasons.")
    }
    if (truncatedCount > 0) {
        summary.append("$IMPORT_TRUNCATED_PREFIX$truncatedCount$IMPORT_TRUNCATED_SUFFIX")
    }
    return summary.toString()
}

private fun ImportRejectionReasonModel.toLabel(): String =
    when (this) {
        ImportRejectionReasonModel.FILE_TOO_LARGE -> REASON_FILE_TOO_LARGE
        ImportRejectionReasonModel.TOO_MANY_MESSAGES -> REASON_TOO_MANY_MESSAGES
        ImportRejectionReasonModel.HIDDEN_MARKUP -> REASON_HIDDEN_MARKUP
        ImportRejectionReasonModel.DENSE_INVISIBLE_CHARS -> REASON_DENSE_INVISIBLE_CHARS
        ImportRejectionReasonModel.INPUT_GUARD_BLOCKED -> REASON_INPUT_GUARD_BLOCKED
    }
