package com.jarvis.chat.feature.chat.data.mapper

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.data.model.ChatHistoryDataModel
import com.jarvis.chat.feature.chat.data.model.ChatMessageDataModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel

private const val AUTHOR_USER = "USER"
private const val AUTHOR_ASSISTANT = "ASSISTANT"
private const val HISTORY_VERSION = 1

internal fun HistoryMessageModel.toChatMessageDataModel(): ChatMessageDataModel =
    ChatMessageDataModel(
        id = id,
        author = when (author) {
            MessageAuthor.USER -> AUTHOR_USER
            MessageAuthor.ASSISTANT -> AUTHOR_ASSISTANT
        },
        text = text,
        isFavorite = isFavorite,
    )

internal fun List<HistoryMessageModel>.toChatHistoryDataModel(): ChatHistoryDataModel =
    ChatHistoryDataModel(
        version = HISTORY_VERSION,
        messages = map { message -> message.toChatMessageDataModel() },
    )
