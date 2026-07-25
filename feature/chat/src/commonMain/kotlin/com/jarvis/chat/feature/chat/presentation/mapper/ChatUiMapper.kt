package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.presentation.model.ChatMessageUiModel
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import com.jarvis.chat.feature.chat.presentation.model.ChatUiModel
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime
import kotlin.time.Instant

private const val TIME_LABEL_PAD_LENGTH = 2
private const val TIME_LABEL_PAD_CHAR = '0'
private const val TIME_LABEL_SEPARATOR = ":"

internal class ChatUiMapper : UiMapper<ChatState, ChatUiModel> {

    override fun map(state: ChatState): ChatUiModel {
        val visibleMessages = if (state.isFavoritesFilterActive) {
            state.messages.filter { message -> message.isFavorite }
        } else {
            state.messages
        }
        return ChatUiModel(
            messages = visibleMessages.map { message -> message.toChatMessageUiModel() },
            inputText = state.inputText,
            isLoading = state.isLoading && !state.isFavoritesFilterActive,
            isSendEnabled = state.inputText.isNotBlank() && !state.isLoading,
            isErrorVisible = state.hasError && !state.isFavoritesFilterActive,
            isFavoritesFilterActive = state.isFavoritesFilterActive,
            favoritesCount = state.messages.count { message -> message.isFavorite },
            showClearConfirmation = state.showClearConfirmation,
            isEmptyState = state.messages.isEmpty() &&
                !state.isLoading &&
                !state.hasError &&
                !state.isFavoritesFilterActive,
            isFavoritesEmptyState = state.isFavoritesFilterActive && visibleMessages.isEmpty(),
        )
    }

    private fun HistoryMessageModel.toChatMessageUiModel(): ChatMessageUiModel {
        val isFromUser = author == MessageAuthor.USER
        return ChatMessageUiModel(
            id = id,
            text = text,
            isFromUser = isFromUser,
            isSpeakable = !isFromUser,
            isFavorite = isFavorite,
            canFavorite = !isFromUser,
            timeLabel = timestamp.toTimeLabel(),
        )
    }
}

private fun Long.toTimeLabel(): String {
    val dateTime = Instant.fromEpochMilliseconds(this).toLocalDateTime(TimeZone.currentSystemDefault())
    val hour = dateTime.hour.toString().padStart(TIME_LABEL_PAD_LENGTH, TIME_LABEL_PAD_CHAR)
    val minute = dateTime.minute.toString().padStart(TIME_LABEL_PAD_LENGTH, TIME_LABEL_PAD_CHAR)
    return "$hour$TIME_LABEL_SEPARATOR$minute"
}
