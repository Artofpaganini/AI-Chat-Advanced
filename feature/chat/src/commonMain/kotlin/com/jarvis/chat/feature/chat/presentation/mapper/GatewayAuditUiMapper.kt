package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.ai.domain.model.GatewayAuditEntryModel
import com.jarvis.chat.feature.ai.domain.model.GatewayLoadErrorModel
import com.jarvis.chat.feature.ai.domain.model.GatewayStatsModel
import com.jarvis.chat.feature.chat.presentation.model.GatewayAuditEntryUiModel
import com.jarvis.chat.feature.chat.presentation.model.GatewayAuditState
import com.jarvis.chat.feature.chat.presentation.model.GatewayAuditUiModel
import com.jarvis.chat.feature.chat.presentation.model.GatewayStatsUiModel

private const val REASONS_EMPTY_LABEL = "-"
private const val REASON_SEPARATOR = ", "
private const val TOKENS_IN_SUFFIX = " вход"
private const val TOKENS_OUT_PREFIX = " / "
private const val TOKENS_OUT_SUFFIX = " выход"
private const val COST_PREFIX = "$"
private const val LATENCY_SUFFIX = " мс"

private const val TOTAL_REQUESTS_PREFIX = "Запросов: "
private const val BLOCKED_PREFIX = "Заблокировано: "
private const val BLOCKED_SEPARATOR = " (вход "
private const val BLOCKED_MIDDLE = " · выход "
private const val BLOCKED_SUFFIX = ")"
private const val MASKED_PREFIX = "Замаскировано: "
private const val RATE_LIMITED_PREFIX = "Отбито по частоте: "
private const val ERROR_MESSAGE_NO_CONNECTION = "Gateway недоступен. Проверьте, что шлюз запущен, и повторите."
private const val ERROR_MESSAGE_PARSE_FAILED =
    "Шлюз ответил, но ответ не удалось разобрать. Формат ответа не совпадает с ожидаемым."
private const val ERROR_MESSAGE_UNKNOWN = "Не удалось загрузить журнал шлюза. Попробуйте ещё раз."

internal class GatewayAuditUiMapper : UiMapper<GatewayAuditState, GatewayAuditUiModel> {

    override fun map(state: GatewayAuditState): GatewayAuditUiModel =
        GatewayAuditUiModel(
            isSheetVisible = state.isSheetVisible,
            isLoading = state.isLoading,
            entries = state.entries.map { entry -> entry.toGatewayAuditEntryUiModel() },
            statsSummary = state.stats?.toGatewayStatsUiModel(),
            isEmptyState = !state.isLoading && state.entries.isEmpty(),
            errorMessage = state.error?.toGatewayLoadErrorMessage(),
        )

    private fun GatewayAuditEntryModel.toGatewayAuditEntryUiModel(): GatewayAuditEntryUiModel {
        val reasonLabels = (inputReasons + outputReasons).map { reason -> reason.toGatewayReasonLabel() }
        return GatewayAuditEntryUiModel(
            requestId = requestId,
            timeLabel = timestamp,
            verdictLabel = verdict.toShortVerdictLabel(),
            reasonsLabel = reasonLabels.takeIf { labels -> labels.isNotEmpty() }
                ?.joinToString(REASON_SEPARATOR)
                ?: REASONS_EMPTY_LABEL,
            maskedCount = maskedCount,
            tokensLabel = "$tokensIn$TOKENS_IN_SUFFIX$TOKENS_OUT_PREFIX$tokensOut$TOKENS_OUT_SUFFIX",
            costLabel = "$COST_PREFIX${costUsd.toGatewayCostLabel()}",
            latencyLabel = "$latencyMs$LATENCY_SUFFIX",
        )
    }

    private fun GatewayStatsModel.toGatewayStatsUiModel(): GatewayStatsUiModel =
        GatewayStatsUiModel(
            totalRequestsLabel = "$TOTAL_REQUESTS_PREFIX$totalRequests",
            blockedLabel = "$BLOCKED_PREFIX${blockedInputCount + blockedOutputCount}" +
                "$BLOCKED_SEPARATOR$blockedInputCount$BLOCKED_MIDDLE$blockedOutputCount$BLOCKED_SUFFIX",
            maskedLabel = "$MASKED_PREFIX$maskedCount",
            rateLimitedLabel = "$RATE_LIMITED_PREFIX$rateLimitedCount",
            tokensLabel = "$totalTokensIn$TOKENS_IN_SUFFIX$TOKENS_OUT_PREFIX$totalTokensOut$TOKENS_OUT_SUFFIX",
            costLabel = "$COST_PREFIX${totalCostUsd.toGatewayCostLabel()}",
        )
}

internal fun GatewayLoadErrorModel.toGatewayLoadErrorMessage(): String =
    when (this) {
        GatewayLoadErrorModel.NoConnection -> ERROR_MESSAGE_NO_CONNECTION
        GatewayLoadErrorModel.ParseFailed -> ERROR_MESSAGE_PARSE_FAILED
        GatewayLoadErrorModel.Unknown -> ERROR_MESSAGE_UNKNOWN
    }
