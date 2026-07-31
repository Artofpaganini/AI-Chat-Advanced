package com.jarvis.chat.core.micromodel.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class MicroModelAnalyzerDataModel(
    val kind: String,
    @SerialName("ngram_min")
    val ngramMin: Int,
    @SerialName("ngram_max")
    val ngramMax: Int,
)
