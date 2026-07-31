package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.core.micromodel.domain.model.MicroTriageRouteModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageStatusModel
import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageStatusModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.RouteDecisionModel
import com.jarvis.chat.feature.chat.domain.model.RouteSourceModel
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
private const val CONFIDENCE_DECIMAL_PAD_LENGTH = 2
private const val CONFIDENCE_DECIMAL_PAD_CHAR = '0'
private const val ROUTE_BADGE_LOCAL_PREFIX = "локально"
private const val ROUTE_BADGE_CLOUD_PREFIX = "облако"
private const val ROUTE_BADGE_SEPARATOR = " · "
private const val ROUTE_BADGE_MS_SUFFIX = " мс"
private const val ROUTE_BADGE_ARROW = " -> "
private const val ROUTE_BADGE_RAISED_PREFIX = " (поднято с "
private const val ROUTE_BADGE_RAISED_SUFFIX = ")"
private const val ROUTE_BADGE_HELD_PREFIX = " (экстренный маршрут удержан вопреки "
private const val ROUTE_BADGE_HELD_SUFFIX = " от LLM)"
private const val SESSION_SUMMARY_PREFIX = "Локально обработано: "
private const val SESSION_SUMMARY_SEPARATOR = " из "
private const val SESSION_SUMMARY_SAVED_PREFIX = " · сэкономлено вызовов LLM: "
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
            microModelSessionSummary = state.toMicroModelSessionSummaryOrNull(),
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
            routeBadgeText = if (isFromUser) null else routeDecision?.toRouteBadgeText(triage),
        )
    }
}

private fun ChatState.toMicroModelSessionSummaryOrNull(): String? {
    if (totalRoutedCount <= 0) {
        return null
    }
    return "$SESSION_SUMMARY_PREFIX$localHandledCount$SESSION_SUMMARY_SEPARATOR$totalRoutedCount" +
        "$SESSION_SUMMARY_SAVED_PREFIX$localHandledCount"
}

private fun RouteDecisionModel.toRouteBadgeText(triage: TriageModel?): String =
    when (source) {
        RouteSourceModel.LOCAL ->
            "$ROUTE_BADGE_LOCAL_PREFIX$ROUTE_BADGE_SEPARATOR${microRoute.name}$ROUTE_BADGE_SEPARATOR" +
                "${microConfidence.toTwoDecimalString()}$ROUTE_BADGE_SEPARATOR$elapsedMillis$ROUTE_BADGE_MS_SUFFIX"
        RouteSourceModel.CLOUD -> {
            val base = "$ROUTE_BADGE_CLOUD_PREFIX$ROUTE_BADGE_SEPARATOR" +
                "${MicroTriageStatusModel.UNSURE.name} ${microConfidence.toTwoDecimalString()}"
            val finalRouteName = triage?.route?.name
            val withFinalRoute = if (finalRouteName != null) "$base$ROUTE_BADGE_ARROW$finalRouteName" else base
            val preMergeRouteName = llmRouteBeforeMerge?.name
            when {
                preMergeRouteName == null || preMergeRouteName == finalRouteName -> withFinalRoute
                microRoute == MicroTriageRouteModel.EMERGENCY ->
                    "$withFinalRoute$ROUTE_BADGE_HELD_PREFIX$preMergeRouteName$ROUTE_BADGE_HELD_SUFFIX"
                else ->
                    "$withFinalRoute$ROUTE_BADGE_RAISED_PREFIX$preMergeRouteName$ROUTE_BADGE_RAISED_SUFFIX"
            }
        }
    }

private fun Double.toTwoDecimalString(): String {
    val roundedHundredths = (this * CONFIDENCE_PERCENT_MULTIPLIER).roundToInt()
    val wholePart = roundedHundredths / CONFIDENCE_PERCENT_MULTIPLIER
    val fractionPart = roundedHundredths % CONFIDENCE_PERCENT_MULTIPLIER
    return "$wholePart.${fractionPart.toString().padStart(CONFIDENCE_DECIMAL_PAD_LENGTH, CONFIDENCE_DECIMAL_PAD_CHAR)}"
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
