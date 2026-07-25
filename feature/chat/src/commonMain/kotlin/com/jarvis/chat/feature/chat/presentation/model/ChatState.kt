package com.jarvis.chat.feature.chat.presentation.model

import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel

internal data class ChatState(
    val messages: List<HistoryMessageModel> = emptyList(),
    val inputText: String = "",
    val isLoading: Boolean = false,
    val error: AiErrorModel? = null,
    val isFavoritesFilterActive: Boolean = false,
    val lastSentText: String = "",
    val showClearConfirmation: Boolean = false,
)
