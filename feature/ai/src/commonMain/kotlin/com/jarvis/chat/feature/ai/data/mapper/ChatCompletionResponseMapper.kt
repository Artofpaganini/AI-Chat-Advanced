package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatStreamChunkDataModel
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor

internal fun ChatCompletionResponseModel.toChatMessageModel(): ChatMessageModel =
    ChatMessageModel(
        author = MessageAuthor.ASSISTANT,
        text = choices.firstOrNull()?.message?.content.orEmpty().trim(),
        modelId = model,
    )

internal fun ChatCompletionResponseModel.toChatStreamChunkDataModel(): ChatStreamChunkDataModel =
    ChatStreamChunkDataModel(
        text = choices.firstOrNull()?.message?.content.orEmpty().trim(),
        modelId = model,
        triage = triage,
    )
