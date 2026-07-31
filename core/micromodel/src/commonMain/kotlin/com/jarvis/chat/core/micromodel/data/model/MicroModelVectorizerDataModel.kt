package com.jarvis.chat.core.micromodel.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class MicroModelVectorizerDataModel(
    val kind: String,
    val norm: String,
    val analyzers: List<MicroModelAnalyzerDataModel>,
    val vocabulary: Map<String, MicroModelVocabularyEntryDataModel>,
)
