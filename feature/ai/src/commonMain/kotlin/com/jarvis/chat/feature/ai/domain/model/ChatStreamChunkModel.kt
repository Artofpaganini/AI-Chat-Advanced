package com.jarvis.chat.feature.ai.domain.model

data class ChatStreamChunkModel(
    val text: String,
    val modelId: String? = null,
    val triage: TriageModel? = null,
    val gatewaySignal: GatewaySignalModel? = null,
    val outputTruncation: GatewayOutputTruncationModel? = null,
)
