package com.jarvis.chat.feature.ai.domain.model

data class CodeLoopStageEventModel(
    val stage: CodeLoopStageModel,
    val iteration: Int?,
    val status: CodeLoopStatusModel,
    val files: List<String>,
    val gatewayVerdict: GatewayVerdictModel?,
    val errors: List<String>,
    val findings: List<CodeLoopFindingModel>,
    val commit: String?,
    val iterationsUsed: Int?,
    val securityFindings: Int?,
    val gatewayBlocks: Int?,
    val finalCode: Map<String, String>,
)
