package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class ChatCompletionResponseModel(
    val choices: List<ChatChoiceResponseModel>,
    val model: String? = null,
    val triage: TriageResponseModel? = null,
    val usage: ChatUsageResponseModel? = null,
)
