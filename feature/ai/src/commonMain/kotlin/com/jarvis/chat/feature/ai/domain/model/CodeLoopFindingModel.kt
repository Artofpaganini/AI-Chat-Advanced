package com.jarvis.chat.feature.ai.domain.model

data class CodeLoopFindingModel(
    val severity: CodeLoopSeverityModel,
    val file: String,
    val line: Int,
    val title: String,
    val fix: String,
)
