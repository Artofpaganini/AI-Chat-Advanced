package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class ChatMessageResponseModel(
    val role: String,
    val content: String,
)
