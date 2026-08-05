package com.jarvis.chat.feature.ai.domain.model

data class GatewayStatsModel(
    val totalRequests: Int,
    val blockedInputCount: Int,
    val blockedOutputCount: Int,
    val maskedCount: Int,
    val rateLimitedCount: Int,
    val totalTokensIn: Int,
    val totalTokensOut: Int,
    val totalCostUsd: Double,
    val avgLatencyMs: Int,
)
