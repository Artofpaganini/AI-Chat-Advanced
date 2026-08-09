package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.CodeLoopFindingResponseModel
import com.jarvis.chat.feature.ai.data.model.CodeLoopStageEventResponseModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopFindingModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopSeverityModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageEventModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStatusModel

private const val STATUS_RUNNING = "running"
private const val STATUS_DONE = "done"
private const val STATUS_FAILED = "failed"

internal fun CodeLoopStageEventResponseModel.toCodeLoopStageEventModel(): CodeLoopStageEventModel =
    CodeLoopStageEventModel(
        stage = stage.toCodeLoopStageModel(),
        iteration = iteration,
        status = status.toCodeLoopStatusModel(),
        files = files.orEmpty(),
        gatewayVerdict = gatewayVerdict?.toGatewayVerdictModel(),
        errors = errors.orEmpty(),
        findings = findings.orEmpty().map { finding -> finding.toCodeLoopFindingModel() },
        commit = commit,
        iterationsUsed = iterationsUsed,
        securityFindings = securityFindings,
        gatewayBlocks = gatewayBlocks,
        finalCode = finalCode.orEmpty(),
    )

private fun CodeLoopFindingResponseModel.toCodeLoopFindingModel(): CodeLoopFindingModel =
    CodeLoopFindingModel(
        severity = severity.toCodeLoopSeverityModel(),
        file = file,
        line = line,
        title = title,
        fix = fix,
    )

private fun String.toCodeLoopStageModel(): CodeLoopStageModel =
    CodeLoopStageModel.entries.find { stage -> stage.name == this } ?: CodeLoopStageModel.UNKNOWN

private fun String.toCodeLoopStatusModel(): CodeLoopStatusModel =
    when (this) {
        STATUS_RUNNING -> CodeLoopStatusModel.RUNNING
        STATUS_DONE -> CodeLoopStatusModel.DONE
        STATUS_FAILED -> CodeLoopStatusModel.FAILED
        else -> CodeLoopStatusModel.UNKNOWN
    }

private fun String.toCodeLoopSeverityModel(): CodeLoopSeverityModel =
    CodeLoopSeverityModel.entries.find { severity -> severity.name == this } ?: CodeLoopSeverityModel.UNKNOWN
