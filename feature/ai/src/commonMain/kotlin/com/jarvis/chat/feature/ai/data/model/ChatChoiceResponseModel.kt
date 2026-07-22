package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class ChatChoiceResponseModel(
    val message: ChatMessageResponseModel,
)
