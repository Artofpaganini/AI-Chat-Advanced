package com.jarvis.chat.feature.chat.presentation.model

import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel

internal data class SessionsState(
    val sessions: List<ChatSessionModel> = emptyList(),
    val activeSessionId: String = "",
    val isSheetVisible: Boolean = false,
    val pendingRenameSessionId: String? = null,
    val pendingRenameTitle: String = "",
    val pendingDeleteSessionId: String? = null,
)
