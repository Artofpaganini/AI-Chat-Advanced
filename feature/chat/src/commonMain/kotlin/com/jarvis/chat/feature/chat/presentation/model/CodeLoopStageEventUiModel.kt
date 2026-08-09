package com.jarvis.chat.feature.chat.presentation.model

internal data class CodeLoopStageEventUiModel(
    val title: String,
    val statusLabel: String,
    val contentLines: List<String>,
    val findingLabels: List<String>,
    val isOk: Boolean,
)
