package com.jarvis.chat.feature.chat.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class ChatSessionsIndexDataModel(
    val version: Int,
    val sessions: List<ChatSessionDataModel>,
    val activeSessionId: String,
)
