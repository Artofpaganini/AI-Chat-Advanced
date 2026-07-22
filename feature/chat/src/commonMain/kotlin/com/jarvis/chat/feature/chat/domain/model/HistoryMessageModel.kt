package com.jarvis.chat.feature.chat.domain.model

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor

internal data class HistoryMessageModel(
    val id: String,
    val author: MessageAuthor,
    val text: String,
    val isFavorite: Boolean,
)
