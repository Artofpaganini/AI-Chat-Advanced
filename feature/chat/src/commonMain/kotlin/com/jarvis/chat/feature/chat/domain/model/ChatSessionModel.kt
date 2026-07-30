package com.jarvis.chat.feature.chat.domain.model

internal data class ChatSessionModel(
    val id: String,
    val title: String,
    val createdAt: Long,
    val lastMessageAt: Long,
    val messageCount: Int,
)
