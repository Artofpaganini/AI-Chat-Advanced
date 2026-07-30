package com.jarvis.chat.feature.chat.domain.model

internal data class ChatSessionsModel(
    val sessions: List<ChatSessionModel>,
    val activeSessionId: String,
)
