package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
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
private const val ERROR_MESSAGE_NO_CONNECTION = "No internet connection. Check your network and try again."
private const val ERROR_MESSAGE_TIMEOUT = "The request timed out. Please try again."
private const val ERROR_MESSAGE_UNAUTHORIZED = "Authorization failed. Check your API key in settings."
private const val ERROR_MESSAGE_RATE_LIMITED = "Too many requests. Please wait a moment and try again."
private const val ERROR_MESSAGE_SERVER_ERROR_PREFIX = "Server error ("
private const val ERROR_MESSAGE_SERVER_ERROR_SUFFIX = "). Please try again later."
private const val ERROR_MESSAGE_UNKNOWN = "Something went wrong. Please try again."

internal class ChatUiMapper : UiMapper<ChatState, ChatUiModel> {

    override fun map(state: ChatState): ChatUiModel {
        val visibleMessages = if (state.isFavoritesFilterActive) {
            state.messages.filter { message -> message.isFavorite }
        } else {
            state.messages
        }
        return ChatUiModel(
            messages = visibleMessages.map { message -> message.toChatMessageUiModel(state.speakingMessageId) },
            inputText = state.inputText,
            isLoading = state.isLoading && !state.isFavoritesFilterActive,
            isSendEnabled = state.inputText.isNotBlank() && !state.isLoading,
            isGenerating = state.isLoading,
            isErrorVisible = state.error != null && !state.isFavoritesFilterActive,
            errorMessage = state.error?.toErrorMessage(),
            isFavoritesFilterActive = state.isFavoritesFilterActive,
            favoritesCount = state.messages.count { message -> message.isFavorite },
            showClearConfirmation = state.showClearConfirmation,
            isDeleteMessageConfirmationVisible = state.pendingDeleteMessageId != null,
            isEmptyState = state.messages.isEmpty() &&
                !state.isLoading &&
                state.error == null &&
                !state.isFavoritesFilterActive,
            isFavoritesEmptyState = state.isFavoritesFilterActive && visibleMessages.isEmpty(),
        )
    }

    private fun HistoryMessageModel.toChatMessageUiModel(speakingMessageId: String?): ChatMessageUiModel {
        val isFromUser = author == MessageAuthor.USER
        return ChatMessageUiModel(
            id = id,
            text = text,
            isFromUser = isFromUser,
            isSpeakable = !isFromUser,
            isSpeaking = id == speakingMessageId,
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

private fun AiErrorModel.toErrorMessage(): String = when (this) {
    AiErrorModel.NoConnection -> ERROR_MESSAGE_NO_CONNECTION
    AiErrorModel.Timeout -> ERROR_MESSAGE_TIMEOUT
    AiErrorModel.Unauthorized -> ERROR_MESSAGE_UNAUTHORIZED
    is AiErrorModel.BadRequest -> message
    AiErrorModel.RateLimited -> ERROR_MESSAGE_RATE_LIMITED
    is AiErrorModel.ServerError -> "$ERROR_MESSAGE_SERVER_ERROR_PREFIX$code$ERROR_MESSAGE_SERVER_ERROR_SUFFIX"
    AiErrorModel.Unknown -> ERROR_MESSAGE_UNKNOWN
}
