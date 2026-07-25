package com.jarvis.chat.feature.chat.presentation.model

import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel

internal sealed interface ChatAction {

    sealed interface Ui : ChatAction {

        data class InputChanged(val text: String) : Ui

        data class VoiceTranscribed(val text: String) : Ui

        data object SendClicked : Ui

        data class SuggestionClicked(val text: String) : Ui

        data object RetryClicked : Ui

        data class FavoriteToggled(val messageId: String) : Ui

        data object MessageCopied : Ui

        data object FavoritesFilterToggled : Ui

        data object ExportClicked : Ui

        data class ImportRequested(val json: String) : Ui

        data object ClearHistoryClicked : Ui

        data object ClearHistoryConfirmed : Ui

        data object ClearHistoryCancelled : Ui
    }

    sealed interface Internal : ChatAction {

        data class HistoryLoaded(val messages: List<HistoryMessageModel>) : Internal

        data class ReplyReceived(val message: ChatMessageModel) : Internal

        data class ReplyFailed(val error: AiErrorModel) : Internal

        data class Exported(val filePath: String) : Internal

        data object ExportFailed : Internal

        data class Imported(val messages: List<HistoryMessageModel>) : Internal

        data object ImportFailed : Internal

        data object HistoryCleared : Internal

        data object ClearHistoryFailed : Internal
    }
}
