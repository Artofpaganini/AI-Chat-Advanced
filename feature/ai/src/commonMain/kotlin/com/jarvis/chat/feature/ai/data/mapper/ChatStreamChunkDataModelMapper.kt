package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.ChatStreamChunkDataModel
import com.jarvis.chat.feature.ai.domain.model.ChatStreamChunkModel

internal fun ChatStreamChunkDataModel.toChatStreamChunkModel(): ChatStreamChunkModel =
    ChatStreamChunkModel(text = text, modelId = modelId)
