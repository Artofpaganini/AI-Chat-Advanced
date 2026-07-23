package com.jarvis.chat.feature.ai.domain.repository

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel

interface AiRepository {

    suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel
}
