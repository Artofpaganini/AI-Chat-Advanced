package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class CodeLoopStageEventResponseModel(
    val stage: String,
    val iteration: Int? = null,
    val status: String,
    val files: List<String>? = null,
    @SerialName("gateway_verdict") val gatewayVerdict: String? = null,
    val errors: List<String>? = null,
    val findings: List<CodeLoopFindingResponseModel>? = null,
    val commit: String? = null,
    @SerialName("iterations_used") val iterationsUsed: Int? = null,
    @SerialName("security_findings") val securityFindings: Int? = null,
    @SerialName("gateway_blocks") val gatewayBlocks: Int? = null,
    @SerialName("final_code") val finalCode: Map<String, String>? = null,
)
