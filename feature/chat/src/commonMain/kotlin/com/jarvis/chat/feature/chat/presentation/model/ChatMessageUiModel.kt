package com.jarvis.chat.feature.chat.presentation.model

internal data class ChatMessageUiModel(
    val id: Int,
    val text: String,
    val isFromUser: Boolean,
    val isSpeakable: Boolean,
)
