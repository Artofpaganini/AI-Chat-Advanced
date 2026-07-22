package com.jarvis.chat.feature.chat.domain.mapper

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel

internal fun HistoryMessageModel.toChatMessageModel(): ChatMessageModel =
    ChatMessageModel(
        author = author,
        text = text,
    )
