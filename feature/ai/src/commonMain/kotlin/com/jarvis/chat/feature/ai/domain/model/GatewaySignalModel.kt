package com.jarvis.chat.feature.ai.domain.model

data class GatewaySignalModel(
    val verdict: GatewayVerdictModel,
    val reasons: List<String>,
    val maskedCount: Int,
    val tokensIn: Int,
    val tokensOut: Int,
    val costUsd: Double,
    val rateLimitLimit: Int?,
    val rateLimitRemaining: Int?,
    val requestId: String?,
)
