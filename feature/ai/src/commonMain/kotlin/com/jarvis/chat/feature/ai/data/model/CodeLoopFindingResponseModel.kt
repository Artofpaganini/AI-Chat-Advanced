package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class CodeLoopFindingResponseModel(
    val severity: String,
    val file: String,
    val line: Int,
    val title: String,
    val fix: String,
)
