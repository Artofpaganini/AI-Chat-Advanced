package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.GatewayOutputTruncationResponseModel
import com.jarvis.chat.feature.ai.data.model.GatewaySignalResponseModel
import com.jarvis.chat.feature.ai.domain.model.GatewayOutputTruncationModel
import com.jarvis.chat.feature.ai.domain.model.GatewaySignalModel
import com.jarvis.chat.feature.ai.domain.model.GatewayVerdictModel
import io.ktor.http.Headers

private const val HEADER_VERDICT = "X-Gateway-Verdict"
private const val HEADER_REASONS = "X-Gateway-Reasons"
private const val HEADER_MASKED_COUNT = "X-Gateway-Masked-Count"
private const val HEADER_TOKENS_IN = "X-Gateway-Tokens-In"
private const val HEADER_TOKENS_OUT = "X-Gateway-Tokens-Out"
private const val HEADER_COST_USD = "X-Gateway-Cost-Usd"
private const val HEADER_RATE_LIMIT_LIMIT = "X-Gateway-RateLimit-Limit"
private const val HEADER_RATE_LIMIT_REMAINING = "X-Gateway-RateLimit-Remaining"
private const val HEADER_REQUEST_ID = "X-Gateway-Request-Id"
private const val REASONS_SEPARATOR = ","

private const val VERDICT_PASS = "pass"
private const val VERDICT_MASKED = "masked"
private const val VERDICT_BLOCKED_INPUT = "blocked_input"
private const val VERDICT_BLOCKED_OUTPUT = "blocked_output"
private const val VERDICT_RATE_LIMITED = "rate_limited"

internal fun Headers.toGatewaySignalResponseModelOrNull(): GatewaySignalResponseModel? {
    val verdict = this[HEADER_VERDICT] ?: return null
    return GatewaySignalResponseModel(
        verdict = verdict,
        reasons = this[HEADER_REASONS]
            ?.split(REASONS_SEPARATOR)
            ?.map { reason -> reason.trim() }
            ?.filter { reason -> reason.isNotEmpty() }
            .orEmpty(),
        maskedCount = this[HEADER_MASKED_COUNT]?.toIntOrNull(),
        tokensIn = this[HEADER_TOKENS_IN]?.toIntOrNull(),
        tokensOut = this[HEADER_TOKENS_OUT]?.toIntOrNull(),
        costUsd = this[HEADER_COST_USD]?.toDoubleOrNull(),
        rateLimitLimit = this[HEADER_RATE_LIMIT_LIMIT]?.toIntOrNull(),
        rateLimitRemaining = this[HEADER_RATE_LIMIT_REMAINING]?.toIntOrNull(),
        requestId = this[HEADER_REQUEST_ID],
    )
}

internal fun GatewaySignalResponseModel.toGatewaySignalModel(): GatewaySignalModel =
    GatewaySignalModel(
        verdict = verdict.toGatewayVerdictModel(),
        reasons = reasons,
        maskedCount = maskedCount ?: 0,
        tokensIn = tokensIn ?: 0,
        tokensOut = tokensOut ?: 0,
        costUsd = costUsd ?: 0.0,
        rateLimitLimit = rateLimitLimit,
        rateLimitRemaining = rateLimitRemaining,
        requestId = requestId,
    )

internal fun GatewayOutputTruncationResponseModel.toGatewayOutputTruncationModel(): GatewayOutputTruncationModel =
    GatewayOutputTruncationModel(
        verdict = verdict.toGatewayVerdictModel(),
        reasons = reasons,
        truncatedAtChars = truncatedAtChars,
    )

internal fun String?.toGatewayVerdictModel(): GatewayVerdictModel =
    when (this) {
        VERDICT_PASS -> GatewayVerdictModel.PASS
        VERDICT_MASKED -> GatewayVerdictModel.MASKED
        VERDICT_BLOCKED_INPUT -> GatewayVerdictModel.BLOCKED_INPUT
        VERDICT_BLOCKED_OUTPUT -> GatewayVerdictModel.BLOCKED_OUTPUT
        VERDICT_RATE_LIMITED -> GatewayVerdictModel.RATE_LIMITED
        else -> GatewayVerdictModel.UNKNOWN
    }
