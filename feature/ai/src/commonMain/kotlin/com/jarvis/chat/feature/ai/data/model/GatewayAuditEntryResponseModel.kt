package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class GatewayAuditEntryResponseModel(
    val ts: String = "",
    @SerialName("request_id") val requestId: String = "",
    @SerialName("client_ip") val clientIp: String = "",
    val model: String = "",
    val verdict: String = "",
    @SerialName("input_reasons") val inputReasons: List<String> = emptyList(),
    @SerialName("output_reasons") val outputReasons: List<String> = emptyList(),
    @SerialName("masked_count") val maskedCount: Int = 0,
    @SerialName("messages_hash") val messagesHash: String = "",
    @SerialName("prompt_preview") val promptPreview: String = "",
    @SerialName("tokens_in") val tokensIn: Int? = null,
    @SerialName("tokens_out") val tokensOut: Int? = null,
    @SerialName("cost_usd") val costUsd: Double? = null,
    @SerialName("latency_ms") val latencyMs: Int? = null,
    @SerialName("upstream_status") val upstreamStatus: Int? = null,
)
