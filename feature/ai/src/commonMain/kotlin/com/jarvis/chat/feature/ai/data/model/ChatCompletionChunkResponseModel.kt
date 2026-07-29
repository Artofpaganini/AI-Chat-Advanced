package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class ChatCompletionChunkResponseModel(
    val choices: List<ChatChunkChoiceResponseModel>,
    val model: String? = null,
    val triage: TriageResponseModel? = null,
)
