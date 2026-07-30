package com.jarvis.chat.feature.chat.presentation.model

internal data class ChatSessionItemUiModel(
    val id: String,
    val title: String,
    val lastMessageTimeLabel: String,
    val messageCount: Int,
    val isActive: Boolean,
)
