package com.jarvis.chat.feature.ai.domain.model

data class CodeLoopRunModel(
    val task: String,
    val events: List<CodeLoopStageEventModel>,
    val isRunning: Boolean,
    val commit: String?,
    val iterationsUsed: Int?,
    val securityFindingsTotal: Int?,
    val gatewayBlocksTotal: Int?,
    val finalCode: Map<String, String>,
    val error: CodeLoopErrorModel?,
)
