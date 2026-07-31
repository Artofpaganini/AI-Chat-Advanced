package com.jarvis.chat.feature.chat.presentation.model

import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageResultModel
import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel

internal sealed interface ChatAction {

    sealed interface Ui : ChatAction {

        data class InputChanged(val text: String) : Ui

        data class VoiceTranscribed(val text: String) : Ui

        data object SendClicked : Ui

        data object StopClicked : Ui

        data class SuggestionClicked(val text: String) : Ui

        data object RetryClicked : Ui

        data class FavoriteToggled(val messageId: String) : Ui

        data class SpeakToggled(val messageId: String) : Ui

        data class SpeechFinished(val messageId: String) : Ui

        data object MessageCopied : Ui

        data object FavoritesFilterToggled : Ui

        data object ExportClicked : Ui

        data class ImportRequested(val json: String) : Ui

        data object ClearHistoryClicked : Ui

        data object ClearHistoryConfirmed : Ui

        data object ClearHistoryCancelled : Ui

        data class DeleteMessageClicked(val messageId: String) : Ui

        data object DeleteMessageConfirmed : Ui

        data object DeleteMessageCancelled : Ui
    }

    sealed interface Internal : ChatAction {

        data class ActiveSessionChanged(val sessionId: String) : Internal

        data class HistoryLoaded(val sessionId: String, val messages: List<HistoryMessageModel>) : Internal

        data class ReplyChunkReceived(
            val sessionId: String,
            val messageId: String,
            val textChunk: String,
            val modelId: String? = null,
            val triage: TriageModel? = null,
            val multiStage: MultiStageResultModel? = null,
        ) : Internal

        data class ReplyCompleted(val sessionId: String) : Internal

        data class ReplyFailed(val sessionId: String, val messageId: String, val error: AiErrorModel) : Internal

        data class Exported(val filePath: String) : Internal

        data object ExportFailed : Internal

        data class Imported(val messages: List<HistoryMessageModel>) : Internal

        data object ImportFailed : Internal

        data object HistoryCleared : Internal

        data object ClearHistoryFailed : Internal

        data class MessageDeleted(val messages: List<HistoryMessageModel>) : Internal

        data object DeleteMessageFailed : Internal
    }
}
