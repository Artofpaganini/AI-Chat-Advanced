package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class CodeLoopRunRequestModel(
    val task: String,
    @SerialName("max_iterations") val maxIterations: Int,
)
