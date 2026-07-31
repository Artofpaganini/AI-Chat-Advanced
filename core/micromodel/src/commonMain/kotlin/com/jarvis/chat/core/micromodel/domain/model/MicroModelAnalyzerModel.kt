package com.jarvis.chat.core.micromodel.domain.model

internal data class MicroModelAnalyzerModel(
    val kind: MicroModelAnalyzerKindModel,
    val ngramMin: Int,
    val ngramMax: Int,
)
