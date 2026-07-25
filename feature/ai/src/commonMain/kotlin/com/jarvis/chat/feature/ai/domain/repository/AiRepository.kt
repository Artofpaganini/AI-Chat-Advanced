package com.jarvis.chat.feature.ai.domain.repository

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import kotlinx.coroutines.flow.Flow

interface AiRepository {

    suspend fun sendMessage(history: List<ChatMessageModel>): ChatMessageModel

    fun sendMessageStream(history: List<ChatMessageModel>): Flow<String>
}
