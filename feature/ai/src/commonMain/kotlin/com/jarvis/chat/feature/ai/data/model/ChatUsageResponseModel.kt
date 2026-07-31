package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class ChatUsageResponseModel(
    @SerialName("prompt_tokens")
    val promptTokens: Int? = null,
    @SerialName("completion_tokens")
    val completionTokens: Int? = null,
)
