package com.jarvis.chat.feature.ai.data.model

internal data class ChatStreamChunkDataModel(
    val text: String,
    val modelId: String? = null,
    val triage: TriageResponseModel? = null,
)
