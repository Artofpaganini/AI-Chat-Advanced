package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateRequestModel(
    val model: String = "deepseek-chat",
    val messages: List<TranslateMessageRequestModel>,
)
