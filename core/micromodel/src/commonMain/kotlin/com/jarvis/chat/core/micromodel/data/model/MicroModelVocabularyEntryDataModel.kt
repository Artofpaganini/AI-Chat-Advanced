package com.jarvis.chat.core.micromodel.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class MicroModelVocabularyEntryDataModel(
    val i: Int,
    val idf: Double,
)
