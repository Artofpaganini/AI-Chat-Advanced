package com.jarvis.chat.feature.ai.data.model

internal data class GatewaySignalResponseModel(
    val verdict: String?,
    val reasons: List<String>,
    val maskedCount: Int?,
    val tokensIn: Int?,
    val tokensOut: Int?,
    val costUsd: Double?,
    val rateLimitLimit: Int?,
    val rateLimitRemaining: Int?,
    val requestId: String?,
)
