package com.jarvis.chat.feature.ai.domain.repository

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel

internal interface AiRepository {

    suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel
}
