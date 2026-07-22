package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor

private const val ROLE_USER = "user"
private const val ROLE_ASSISTANT = "assistant"

internal fun ChatMessageModel.toChatMessageRequestModel(): ChatMessageRequestModel =
    ChatMessageRequestModel(
        role = when (author) {
            MessageAuthor.USER -> ROLE_USER
            MessageAuthor.ASSISTANT -> ROLE_ASSISTANT
        },
        content = text,
    )
