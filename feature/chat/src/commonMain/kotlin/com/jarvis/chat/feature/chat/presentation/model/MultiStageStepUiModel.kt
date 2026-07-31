package com.jarvis.chat.feature.chat.presentation.model

internal data class MultiStageStepUiModel(
    val title: String,
    val contentLines: List<String>,
    val metaLabel: String,
    val violationLabels: List<String>,
    val errorLabel: String?,
    val isOk: Boolean,
)
