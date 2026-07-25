package com.jarvis.chat.feature.chat.presentation.model

import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel

internal data class ChatState(
    val messages: List<HistoryMessageModel> = emptyList(),
    val inputText: String = "",
    val isLoading: Boolean = false,
    val hasError: Boolean = false,
    val isFavoritesFilterActive: Boolean = false,
    val lastSentText: String = "",
    val showClearConfirmation: Boolean = false,
)
