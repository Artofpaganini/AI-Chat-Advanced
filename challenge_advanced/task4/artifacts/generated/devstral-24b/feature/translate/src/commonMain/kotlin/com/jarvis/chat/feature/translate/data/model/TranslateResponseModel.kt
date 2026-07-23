package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateResponseModel(
    val choices: List<TranslateChoiceResponseModel>
)

@Serializable
internal data class TranslateChoiceResponseModel(
    val message: TranslateMessageResponseModel
)

@Serializable
internal data class TranslateMessageResponseModel(
    val role: String,
    val content: String
)
