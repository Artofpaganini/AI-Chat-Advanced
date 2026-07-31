package com.jarvis.chat.feature.ai.domain.model

data class MultiStageStepMetaModel(
    val rawText: String,
    val latencyMs: Long,
    val promptTokens: Int?,
    val completionTokens: Int?,
    val costUsd: Double?,
    val violations: List<MultiStageViolationModel>,
    val isOk: Boolean,
    val errorText: String?,
)
