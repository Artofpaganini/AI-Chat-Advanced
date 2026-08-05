package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class GatewayStatsResponseModel(
    @SerialName("requests_total") val requestsTotal: Int = 0,
    @SerialName("by_verdict") val byVerdict: Map<String, Int> = emptyMap(),
    @SerialName("masked_count_total") val maskedCountTotal: Int = 0,
    @SerialName("tokens_in_total") val tokensInTotal: Int = 0,
    @SerialName("tokens_out_total") val tokensOutTotal: Int = 0,
    @SerialName("cost_usd_total") val costUsdTotal: Double = 0.0,
    @SerialName("avg_latency_ms") val avgLatencyMs: Int? = null,
)
