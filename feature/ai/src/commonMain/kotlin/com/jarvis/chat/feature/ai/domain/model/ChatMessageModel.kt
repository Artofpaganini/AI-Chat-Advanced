package com.jarvis.chat.feature.ai.domain.model

data class ChatMessageModel(
    val author: MessageAuthor,
    val text: String,
    val modelId: String? = null,
)
