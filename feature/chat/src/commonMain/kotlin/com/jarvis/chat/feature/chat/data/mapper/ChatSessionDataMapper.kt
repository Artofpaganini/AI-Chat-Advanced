package com.jarvis.chat.feature.chat.data.mapper

import com.jarvis.chat.feature.chat.data.model.ChatSessionDataModel
import com.jarvis.chat.feature.chat.data.model.ChatSessionsIndexDataModel
import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel
import com.jarvis.chat.feature.chat.domain.model.ChatSessionsModel

internal fun ChatSessionDataModel.toChatSessionModel(): ChatSessionModel =
    ChatSessionModel(
        id = id,
        title = title,
        createdAt = createdAt,
        lastMessageAt = lastMessageAt,
        messageCount = messageCount,
    )

internal fun ChatSessionsIndexDataModel.toChatSessionsModel(): ChatSessionsModel =
    ChatSessionsModel(
        sessions = sessions.map { session -> session.toChatSessionModel() },
        activeSessionId = activeSessionId,
    )
