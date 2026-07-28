package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.ChatCompletionChunkResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatStreamChunkDataModel

internal fun ChatCompletionChunkResponseModel.toDeltaTextOrNull(): String? =
    choices.firstOrNull()?.delta?.content?.takeIf { content -> content.isNotEmpty() }

internal fun ChatCompletionChunkResponseModel.toModelIdOrNull(): String? =
    model?.takeIf { modelId -> modelId.isNotBlank() }

internal fun ChatCompletionChunkResponseModel.toChatStreamChunkDataModelOrNull(): ChatStreamChunkDataModel? {
    val text = toDeltaTextOrNull().orEmpty()
    val modelId = toModelIdOrNull()
    return if (text.isEmpty() && modelId == null) {
        null
    } else {
        ChatStreamChunkDataModel(text = text, modelId = modelId)
    }
}
