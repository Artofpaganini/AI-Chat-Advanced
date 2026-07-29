package com.jarvis.chat.feature.chat.presentation.model

internal data class ChatMessageUiModel(
    val id: String,
    val text: String,
    val isFromUser: Boolean,
    val isSpeakable: Boolean,
    val isSpeaking: Boolean,
    val isFavorite: Boolean,
    val canFavorite: Boolean,
    val timeLabel: String,
    val modelId: String?,
    val triage: TriageUiModel?,
)
