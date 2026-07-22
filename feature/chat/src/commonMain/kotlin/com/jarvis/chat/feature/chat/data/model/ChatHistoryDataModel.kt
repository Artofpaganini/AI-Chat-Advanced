package com.jarvis.chat.feature.chat.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class ChatHistoryDataModel(
    val version: Int,
    val messages: List<ChatMessageDataModel>,
)
