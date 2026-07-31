package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class ChatCompletionRequestModel(
    val model: String,
    val messages: List<ChatMessageRequestModel>,
    val stream: Boolean,
    val adapters: String? = null,
    @SerialName("max_tokens")
    val maxTokens: Int? = null,
    val temperature: Double? = null,
    @SerialName("repetition_penalty")
    val repetitionPenalty: Double? = null,
    @SerialName("reasoning_effort")
    val reasoningEffort: String? = null,
)
