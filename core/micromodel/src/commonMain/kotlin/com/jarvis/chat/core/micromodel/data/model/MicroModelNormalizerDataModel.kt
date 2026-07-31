package com.jarvis.chat.core.micromodel.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class MicroModelNormalizerDataModel(
    val lowercase: Boolean = true,
    @SerialName("yo_to_e")
    val yoToE: Boolean = true,
    @SerialName("collapse_whitespace")
    val collapseWhitespace: Boolean = true,
    @SerialName("strip_chars")
    val stripChars: String = "",
    @SerialName("digit_placeholder")
    val digitPlaceholder: String = "0",
)
