package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class ChatCompletionRequestModel(
    val model: String,
    val messages: List<ChatMessageRequestModel>,
    val stream: Boolean,
)
