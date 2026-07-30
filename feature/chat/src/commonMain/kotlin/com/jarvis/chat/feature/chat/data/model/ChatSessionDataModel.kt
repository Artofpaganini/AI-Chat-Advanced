package com.jarvis.chat.feature.chat.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class ChatSessionDataModel(
    val id: String,
    val title: String,
    val createdAt: Long,
    val lastMessageAt: Long,
    val messageCount: Int,
)
