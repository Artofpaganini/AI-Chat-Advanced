package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.core.micromodel.domain.model.MicroTriageRouteModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageStatusModel
import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.model.MultiStageAnswerStepModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageDecideStepModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageDecisionModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageFactsModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageParseStepModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageResultModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageStepMetaModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageViolationModel
import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageStatusModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.RouteDecisionModel
import com.jarvis.chat.feature.chat.domain.model.RouteSourceModel
import com.jarvis.chat.feature.chat.presentation.model.ChatMessageUiModel
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import com.jarvis.chat.feature.chat.presentation.model.ChatUiModel
import com.jarvis.chat.feature.chat.presentation.model.MultiStageStepUiModel
import com.jarvis.chat.feature.chat.presentation.model.MultiStageUiModel
import com.jarvis.chat.feature.chat.presentation.model.TriageRouteUiModel
import com.jarvis.chat.feature.chat.presentation.model.TriageStatusUiModel
import com.jarvis.chat.feature.chat.presentation.model.TriageUiModel
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime
import kotlin.math.roundToInt
import kotlin.math.roundToLong
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
private const val ERROR_MESSAGE_LOCAL_PROVIDER_UNREACHABLE_PREFIX = "Local provider is unreachable at "
private const val ERROR_MESSAGE_LOCAL_PROVIDER_UNREACHABLE_SUFFIX =
    ". Start the local server, or switch to DeepSeek Cloud in Settings."
private const val ERROR_MESSAGE_TIMEOUT = "The request timed out. Please try again."
private const val ERROR_MESSAGE_UNAUTHORIZED = "Authorization failed. Check your API key in settings."
private const val ERROR_MESSAGE_RATE_LIMITED = "Too many requests. Please wait a moment and try again."
private const val ERROR_MESSAGE_SERVER_ERROR_PREFIX = "Server error ("
private const val ERROR_MESSAGE_SERVER_ERROR_SUFFIX = "). Please try again later."
private const val ERROR_MESSAGE_UNKNOWN = "Something went wrong. Please try again."

private const val FACT_FIELD_AGE = "AGE_MONTHS"
private const val FACT_FIELD_SYMPTOMS = "SYMPTOMS"
private const val FACT_FIELD_METRICS = "METRICS"
private const val FACT_FIELD_DURATION = "DURATION"
private const val FACT_FIELD_PARENT_STATE = "PARENT_STATE"
private const val FACT_FIELD_QUESTION_TYPE = "QUESTION_TYPE"
private const val FACT_NONE_VALUE = "none"
private const val FACT_SYMPTOM_SEPARATOR = "; "
private const val FACT_PAIR_SEPARATOR = "="

private const val DECISION_FIELD_ROUTE = "ROUTE"
private const val DECISION_FIELD_CONFIDENCE = "CONFIDENCE"
private const val DECISION_FIELD_WHY = "WHY"
private const val DECISION_FIELD_SEPARATOR = " | "

private const val STAGE_TITLE_PARSE = "Этап 1, разбор"
private const val STAGE_TITLE_DECIDE = "Этап 2, решение"
private const val STAGE_TITLE_ANSWER = "Этап 3, ответ"

private const val VIOLATION_LABEL_S1_PARSE = "этап 1 вернул неразбираемый формат"
private const val VIOLATION_LABEL_S1_ROUTE_LEAKED = "этап 1 назвал маршрут, хотя решать ему запрещено"
private const val VIOLATION_LABEL_S2_PARSE = "этап 2 вернул неразбираемый формат или маршрут вне перечисления"
private const val VIOLATION_LABEL_S3_EMPTY = "этап 3 вернул пустой или слишком короткий текст"

private const val META_LATENCY_SUFFIX = " мс"
private const val META_SEPARATOR = " · "
private const val META_TOKENS_SUFFIX = " ток"

private const val SUMMARY_PREFIX = "Итого: "
private const val SUMMARY_CALLS_SUFFIX = " вызовов"
private const val SUMMARY_LATENCY_SUFFIX = " мс"
private const val SUMMARY_COST_UNKNOWN = "цена неизвестна"

private const val COST_DECIMAL_SCALE = 1_000_000L
private const val COST_FRACTION_DIGITS = 6

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
            routeBadgeText = if (isFromUser) null else routeDecision?.toRouteBadgeText(triage?.route ?: multiStage?.route),
            multiStage = if (isFromUser) null else multiStage?.toMultiStageUiModel(),
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

private fun RouteDecisionModel.toRouteBadgeText(finalRoute: TriageRouteModel?): String =
    when (source) {
        RouteSourceModel.LOCAL ->
            "$ROUTE_BADGE_LOCAL_PREFIX$ROUTE_BADGE_SEPARATOR${microRoute.name}$ROUTE_BADGE_SEPARATOR" +
                "${microConfidence.toTwoDecimalString()}$ROUTE_BADGE_SEPARATOR$elapsedMillis$ROUTE_BADGE_MS_SUFFIX"
        RouteSourceModel.CLOUD -> {
            val base = "$ROUTE_BADGE_CLOUD_PREFIX$ROUTE_BADGE_SEPARATOR" +
                "${MicroTriageStatusModel.UNSURE.name} ${microConfidence.toTwoDecimalString()}"
            val finalRouteName = finalRoute?.name
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
    is AiErrorModel.LocalProviderUnreachable ->
        "$ERROR_MESSAGE_LOCAL_PROVIDER_UNREACHABLE_PREFIX$address$ERROR_MESSAGE_LOCAL_PROVIDER_UNREACHABLE_SUFFIX"
    AiErrorModel.Timeout -> ERROR_MESSAGE_TIMEOUT
    AiErrorModel.Unauthorized -> ERROR_MESSAGE_UNAUTHORIZED
    is AiErrorModel.BadRequest -> message
    AiErrorModel.RateLimited -> ERROR_MESSAGE_RATE_LIMITED
    is AiErrorModel.ServerError -> "$ERROR_MESSAGE_SERVER_ERROR_PREFIX$code$ERROR_MESSAGE_SERVER_ERROR_SUFFIX"
    AiErrorModel.Unknown -> ERROR_MESSAGE_UNKNOWN
}

private fun MultiStageResultModel.toMultiStageUiModel(): MultiStageUiModel =
    MultiStageUiModel(
        parseStep = parseStep.toParseStepUiModel(),
        decideStep = decideStep.toDecideStepUiModel(),
        answerStep = answerStep?.toAnswerStepUiModel(),
        summaryLabel = toSummaryLabel(),
    )

private fun MultiStageParseStepModel.toParseStepUiModel(): MultiStageStepUiModel =
    MultiStageStepUiModel(
        title = STAGE_TITLE_PARSE,
        contentLines = facts.toDisplayLines(),
        metaLabel = meta.toMetaLabel(),
        violationLabels = meta.violations.toViolationLabels(),
        errorLabel = meta.errorText,
        isOk = meta.isOk,
    )

private fun MultiStageDecideStepModel.toDecideStepUiModel(): MultiStageStepUiModel =
    MultiStageStepUiModel(
        title = STAGE_TITLE_DECIDE,
        contentLines = listOf(decision.toDisplayLine()),
        metaLabel = meta.toMetaLabel(),
        violationLabels = meta.violations.toViolationLabels(),
        errorLabel = meta.errorText,
        isOk = meta.isOk,
    )

private fun MultiStageAnswerStepModel.toAnswerStepUiModel(): MultiStageStepUiModel =
    MultiStageStepUiModel(
        title = STAGE_TITLE_ANSWER,
        contentLines = emptyList(),
        metaLabel = meta.toMetaLabel(),
        violationLabels = meta.violations.toViolationLabels(),
        errorLabel = meta.errorText,
        isOk = meta.isOk,
    )

private fun MultiStageFactsModel.toDisplayLines(): List<String> {
    val symptomsValue = if (symptoms.isEmpty()) FACT_NONE_VALUE else symptoms.joinToString(FACT_SYMPTOM_SEPARATOR)
    return listOf(
        "$FACT_FIELD_AGE$FACT_PAIR_SEPARATOR${ageMonths?.toString() ?: FACT_NONE_VALUE}",
        "$FACT_FIELD_SYMPTOMS$FACT_PAIR_SEPARATOR$symptomsValue",
        "$FACT_FIELD_METRICS$FACT_PAIR_SEPARATOR${metrics.ifBlank { FACT_NONE_VALUE }}",
        "$FACT_FIELD_DURATION$FACT_PAIR_SEPARATOR${duration.ifBlank { FACT_NONE_VALUE }}",
        "$FACT_FIELD_PARENT_STATE$FACT_PAIR_SEPARATOR${parentState.ifBlank { FACT_NONE_VALUE }}",
        "$FACT_FIELD_QUESTION_TYPE$FACT_PAIR_SEPARATOR${questionType.name}",
    )
}

private fun MultiStageDecisionModel.toDisplayLine(): String {
    val routeValue = route?.name ?: FACT_NONE_VALUE
    return "$DECISION_FIELD_ROUTE$FACT_PAIR_SEPARATOR$routeValue$DECISION_FIELD_SEPARATOR" +
        "$DECISION_FIELD_CONFIDENCE$FACT_PAIR_SEPARATOR$confidence$DECISION_FIELD_SEPARATOR" +
        "$DECISION_FIELD_WHY$FACT_PAIR_SEPARATOR$why"
}

private fun MultiStageStepMetaModel.toMetaLabel(): String {
    val promptTokensValue = promptTokens
    val completionTokensValue = completionTokens
    val tokensLabel = if (promptTokensValue != null && completionTokensValue != null) {
        "${promptTokensValue + completionTokensValue}$META_TOKENS_SUFFIX"
    } else {
        null
    }
    return listOfNotNull("$latencyMs$META_LATENCY_SUFFIX", tokensLabel).joinToString(META_SEPARATOR)
}

private fun List<MultiStageViolationModel>.toViolationLabels(): List<String> =
    map { violation ->
        val label = when (violation) {
            MultiStageViolationModel.S1_PARSE -> VIOLATION_LABEL_S1_PARSE
            MultiStageViolationModel.S1_ROUTE_LEAKED -> VIOLATION_LABEL_S1_ROUTE_LEAKED
            MultiStageViolationModel.S2_PARSE -> VIOLATION_LABEL_S2_PARSE
            MultiStageViolationModel.S3_EMPTY -> VIOLATION_LABEL_S3_EMPTY
        }
        "${violation.name}: $label"
    }

private fun MultiStageResultModel.toSummaryLabel(): String {
    val costLabel = totalCostUsd?.toCostLabel() ?: SUMMARY_COST_UNKNOWN
    return "$SUMMARY_PREFIX$totalCalls$SUMMARY_CALLS_SUFFIX$META_SEPARATOR" +
        "$totalLatencyMs$SUMMARY_LATENCY_SUFFIX$META_SEPARATOR$costLabel"
}

private fun Double.toCostLabel(): String {
    val scaled = (this * COST_DECIMAL_SCALE).roundToLong()
    val whole = scaled / COST_DECIMAL_SCALE
    val fraction = (scaled % COST_DECIMAL_SCALE).toString().padStart(COST_FRACTION_DIGITS, '0')
    return "$$whole.$fraction"
}
