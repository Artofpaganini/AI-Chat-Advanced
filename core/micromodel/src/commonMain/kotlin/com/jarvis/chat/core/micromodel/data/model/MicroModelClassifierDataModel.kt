package com.jarvis.chat.core.micromodel.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class MicroModelClassifierDataModel(
    val kind: String,
    val bias: List<Double>,
    val weights: Map<String, List<Double>>,
)
