package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageStatusModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.presentation.model.ChatMessageUiModel
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import com.jarvis.chat.feature.chat.presentation.model.ChatUiModel
import com.jarvis.chat.feature.chat.presentation.model.TriageRouteUiModel
import com.jarvis.chat.feature.chat.presentation.model.TriageStatusUiModel
import com.jarvis.chat.feature.chat.presentation.model.TriageUiModel
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime
import kotlin.math.roundToInt
import kotlin.time.Instant

private const val TIME_LABEL_PAD_LENGTH = 2
private const val TIME_LABEL_PAD_CHAR = '0'
private const val TIME_LABEL_SEPARATOR = ":"
private const val CONFIDENCE_PERCENT_MULTIPLIER = 100
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
            modelId = if (isFromUser) null else modelId?.takeIf { value -> value.isNotBlank() },
            triage = if (isFromUser) null else triage?.toTriageUiModel(),
        )
    }
}

private fun TriageModel.toTriageUiModel(): TriageUiModel =
    TriageUiModel(
        route = route.toTriageRouteUiModel(),
        routeLabel = routeLabel,
        status = status.toTriageStatusUiModel(),
        statusLabel = statusLabel,
        confidencePercent = (confidence * CONFIDENCE_PERCENT_MULTIPLIER).roundToInt(),
        explain = explain,
        crisis = crisis,
    )

private fun TriageRouteModel.toTriageRouteUiModel(): TriageRouteUiModel =
    when (this) {
        TriageRouteModel.EMERGENCY -> TriageRouteUiModel.EMERGENCY
        TriageRouteModel.DOCTOR_SOON -> TriageRouteUiModel.DOCTOR_SOON
        TriageRouteModel.SELF_CARE -> TriageRouteUiModel.SELF_CARE
        TriageRouteModel.OFF_TOPIC -> TriageRouteUiModel.OFF_TOPIC
        TriageRouteModel.PARENT_SUPPORT -> TriageRouteUiModel.PARENT_SUPPORT
        TriageRouteModel.DATA_INSIGHT -> TriageRouteUiModel.DATA_INSIGHT
        TriageRouteModel.UNKNOWN -> TriageRouteUiModel.UNKNOWN
    }

private fun TriageStatusModel.toTriageStatusUiModel(): TriageStatusUiModel =
    when (this) {
        TriageStatusModel.OK -> TriageStatusUiModel.OK
        TriageStatusModel.UNSURE -> TriageStatusUiModel.UNSURE
        TriageStatusModel.FAIL -> TriageStatusUiModel.FAIL
        TriageStatusModel.UNKNOWN -> TriageStatusUiModel.UNKNOWN
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
