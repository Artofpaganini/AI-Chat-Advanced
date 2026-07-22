package com.jarvis.chat.feature.chat.presentation.model

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel

internal data class ChatState(
    val messages: List<ChatMessageModel> = emptyList(),
    val inputText: String = "",
    val isLoading: Boolean = false,
    val hasError: Boolean = false,
)
