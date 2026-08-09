package com.jarvis.chat.feature.chat.presentation.model

internal data class CodeLoopRunUiModel(
    val stages: List<CodeLoopStageEventUiModel>,
    val summaryLabel: String,
)
