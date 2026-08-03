package com.jarvis.chat.feature.chat.presentation.model

internal data class ChatUiModel(
    val messages: List<ChatMessageUiModel>,
    val inputText: String,
    val isLoading: Boolean,
    val isSendEnabled: Boolean,
    val isGenerating: Boolean,
    val isErrorVisible: Boolean,
    val errorMessage: String?,
    val isFavoritesFilterActive: Boolean,
    val favoritesCount: Int,
    val showClearConfirmation: Boolean,
    val isDeleteMessageConfirmationVisible: Boolean,
    val isEmptyState: Boolean,
    val isFavoritesEmptyState: Boolean,
    val microModelSessionSummary: String?,
    val injectionGuardSessionSummary: String?,
)
