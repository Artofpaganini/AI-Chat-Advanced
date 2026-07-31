package com.jarvis.chat.core.micromodel.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class MicroModelThresholdsDataModel(
    @SerialName("confident_min_prob")
    val confidentMinProb: Double,
    @SerialName("confident_min_margin")
    val confidentMinMargin: Double,
    @SerialName("always_escalate_labels")
    val alwaysEscalateLabels: List<String>,
)
