package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.ChatCompletionChunkResponseModel

internal fun ChatCompletionChunkResponseModel.toDeltaTextOrNull(): String? =
    choices.firstOrNull()?.delta?.content?.takeIf { content -> content.isNotEmpty() }
