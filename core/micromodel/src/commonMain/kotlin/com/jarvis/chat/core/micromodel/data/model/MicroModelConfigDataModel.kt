package com.jarvis.chat.core.micromodel.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class MicroModelConfigDataModel(
    @SerialName("format_version")
    val formatVersion: Int,
    val labels: List<String>,
    val normalizer: MicroModelNormalizerDataModel,
    val vectorizer: MicroModelVectorizerDataModel,
    val classifier: MicroModelClassifierDataModel,
    val thresholds: MicroModelThresholdsDataModel,
)
