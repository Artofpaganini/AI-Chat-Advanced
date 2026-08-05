package com.jarvis.chat.feature.ai.domain.model

data class GatewayOutputTruncationModel(
    val verdict: GatewayVerdictModel,
    val reasons: List<String>,
    val truncatedAtChars: Int,
)
