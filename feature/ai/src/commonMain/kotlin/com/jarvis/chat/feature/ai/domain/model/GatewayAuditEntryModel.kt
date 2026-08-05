package com.jarvis.chat.feature.ai.domain.model

data class GatewayAuditEntryModel(
    val timestamp: String,
    val requestId: String,
    val clientIp: String,
    val model: String,
    val verdict: GatewayVerdictModel,
    val inputReasons: List<String>,
    val outputReasons: List<String>,
    val maskedCount: Int,
    val messagesHash: String,
    val promptPreview: String,
    val tokensIn: Int,
    val tokensOut: Int,
    val costUsd: Double,
    val latencyMs: Int,
    val upstreamStatus: Int,
)
