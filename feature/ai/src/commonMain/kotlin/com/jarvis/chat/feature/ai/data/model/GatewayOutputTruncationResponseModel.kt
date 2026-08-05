package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class GatewayOutputTruncationResponseModel(
    @SerialName("gateway_output_verdict") val verdict: String = "",
    @SerialName("gateway_output_reasons") val reasons: List<String> = emptyList(),
    @SerialName("gateway_truncated_at_chars") val truncatedAtChars: Int = 0,
)
