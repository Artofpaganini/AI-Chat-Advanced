package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateMessageRequestModel(
    val role: String,
    val content: String
)
