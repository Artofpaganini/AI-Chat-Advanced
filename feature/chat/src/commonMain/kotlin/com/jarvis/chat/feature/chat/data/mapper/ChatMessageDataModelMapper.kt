package com.jarvis.chat.feature.chat.data.mapper

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.data.model.ChatMessageDataModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel

private const val AUTHOR_ASSISTANT = "ASSISTANT"

internal fun ChatMessageDataModel.toHistoryMessageModel(): HistoryMessageModel =
    HistoryMessageModel(
        id = id,
        author = if (author == AUTHOR_ASSISTANT) MessageAuthor.ASSISTANT else MessageAuthor.USER,
        text = text,
        isFavorite = isFavorite,
        timestamp = timestamp,
        modelId = modelId,
    )
