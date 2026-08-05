package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.GatewayAuditEntryResponseModel
import com.jarvis.chat.feature.ai.data.model.GatewayStatsResponseModel
import com.jarvis.chat.feature.ai.domain.model.GatewayAuditEntryModel
import com.jarvis.chat.feature.ai.domain.model.GatewayStatsModel

private const val VERDICT_KEY_BLOCKED_INPUT = "blocked_input"
private const val VERDICT_KEY_BLOCKED_OUTPUT = "blocked_output"
private const val VERDICT_KEY_RATE_LIMITED = "rate_limited"

internal fun GatewayAuditEntryResponseModel.toGatewayAuditEntryModel(): GatewayAuditEntryModel =
    GatewayAuditEntryModel(
        timestamp = ts,
        requestId = requestId,
        clientIp = clientIp,
        model = model,
        verdict = verdict.toGatewayVerdictModel(),
        inputReasons = inputReasons,
        outputReasons = outputReasons,
        maskedCount = maskedCount,
        messagesHash = messagesHash,
        promptPreview = promptPreview,
        tokensIn = tokensIn ?: 0,
        tokensOut = tokensOut ?: 0,
        costUsd = costUsd ?: 0.0,
        latencyMs = latencyMs ?: 0,
        upstreamStatus = upstreamStatus ?: 0,
    )

internal fun GatewayStatsResponseModel.toGatewayStatsModel(): GatewayStatsModel =
    GatewayStatsModel(
        totalRequests = requestsTotal,
        blockedInputCount = byVerdict[VERDICT_KEY_BLOCKED_INPUT] ?: 0,
        blockedOutputCount = byVerdict[VERDICT_KEY_BLOCKED_OUTPUT] ?: 0,
        maskedCount = maskedCountTotal,
        rateLimitedCount = byVerdict[VERDICT_KEY_RATE_LIMITED] ?: 0,
        totalTokensIn = tokensInTotal,
        totalTokensOut = tokensOutTotal,
        totalCostUsd = costUsdTotal,
        avgLatencyMs = avgLatencyMs ?: 0,
    )
