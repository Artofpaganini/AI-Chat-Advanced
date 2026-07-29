package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class TriageResponseModel(
    val route: String? = null,
    @SerialName("route_label")
    val routeLabel: String? = null,
    val status: String? = null,
    @SerialName("status_label")
    val statusLabel: String? = null,
    val confidence: Double? = null,
    @SerialName("red_flags")
    val redFlags: List<String>? = null,
    val votes: List<String>? = null,
    val agreement: Double? = null,
    @SerialName("self_check_ran")
    val selfCheckRan: Boolean? = null,
    @SerialName("escalated_by_safety")
    val escalatedBySafety: Boolean? = null,
    val calls: Int? = null,
    @SerialName("latency_ms")
    val latencyMs: Long? = null,
    val explain: String? = null,
    val crisis: Boolean? = null,
)
