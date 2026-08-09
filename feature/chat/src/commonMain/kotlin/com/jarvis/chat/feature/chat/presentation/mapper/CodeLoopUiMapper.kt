package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.feature.ai.domain.model.CodeLoopFindingModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopRunModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopSeverityModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageEventModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStatusModel
import com.jarvis.chat.feature.chat.presentation.model.CodeLoopRunUiModel
import com.jarvis.chat.feature.chat.presentation.model.CodeLoopStageEventUiModel

private const val CODE_LOOP_ITERATION_LABEL_PREFIX = ", итерация "
private const val CODE_LOOP_STATUS_RUNNING = "выполняется"
private const val CODE_LOOP_STATUS_DONE = "готово"
private const val CODE_LOOP_STATUS_FAILED = "провал"
private const val CODE_LOOP_STATUS_UNKNOWN = "неизвестно"
private const val CODE_LOOP_FILES_PREFIX = "файлы: "
private const val CODE_LOOP_FILES_SEPARATOR = ", "
private const val CODE_LOOP_GATEWAY_PREFIX = "шлюз: "
private const val CODE_LOOP_ERROR_PREFIX = "ошибка: "
private const val CODE_LOOP_COMMIT_LABEL_PREFIX = "коммит: "
private const val CODE_LOOP_FINDING_SEPARATOR = " · "
private const val CODE_LOOP_FINDING_FIX_ARROW = " -> "
private const val CODE_LOOP_SUMMARY_ITERATIONS_PREFIX = "Итого: итераций "
private const val CODE_LOOP_SUMMARY_UNKNOWN = "нет данных"
private const val CODE_LOOP_SUMMARY_FINDINGS_PREFIX = ", находок безопасности "
private const val CODE_LOOP_SUMMARY_SEVERITY_SEPARATOR = " · "
private const val CODE_LOOP_SUMMARY_SEVERITY_VALUE_SEPARATOR = " "
private const val CODE_LOOP_SUMMARY_GATEWAY_PREFIX = ", шлюз заблокировал "
private const val CODE_LOOP_SUMMARY_GATEWAY_SUFFIX = " вызовов"
private const val CODE_LOOP_SEVERITY_LABEL_CRITICAL = "Critical"
private const val CODE_LOOP_SEVERITY_LABEL_HIGH = "High"
private const val CODE_LOOP_SEVERITY_LABEL_MEDIUM = "Medium"
private const val CODE_LOOP_SEVERITY_LABEL_LOW = "Low"

internal fun CodeLoopRunModel.toCodeLoopRunUiModel(): CodeLoopRunUiModel =
    CodeLoopRunUiModel(
        stages = events.map { event -> event.toCodeLoopStageEventUiModel() },
        summaryLabel = toCodeLoopSummaryLabel(),
    )

private fun CodeLoopStageEventModel.toCodeLoopStageEventUiModel(): CodeLoopStageEventUiModel {
    val iterationSuffix = iteration?.let { value -> "$CODE_LOOP_ITERATION_LABEL_PREFIX$value" }.orEmpty()
    val contentLines = buildList {
        if (files.isNotEmpty()) {
            add("$CODE_LOOP_FILES_PREFIX${files.joinToString(CODE_LOOP_FILES_SEPARATOR)}")
        }
        gatewayVerdict?.let { verdict -> add("$CODE_LOOP_GATEWAY_PREFIX${verdict.toShortVerdictLabel()}") }
        commit?.let { commitHash -> add("$CODE_LOOP_COMMIT_LABEL_PREFIX$commitHash") }
        errors.forEach { errorText -> add("$CODE_LOOP_ERROR_PREFIX$errorText") }
    }
    return CodeLoopStageEventUiModel(
        title = "${stage.name}$iterationSuffix",
        statusLabel = status.toCodeLoopStatusLabel(),
        contentLines = contentLines,
        findingLabels = findings.map { finding -> finding.toFindingLabel() },
        isOk = status != CodeLoopStatusModel.FAILED,
    )
}

private fun CodeLoopStatusModel.toCodeLoopStatusLabel(): String =
    when (this) {
        CodeLoopStatusModel.RUNNING -> CODE_LOOP_STATUS_RUNNING
        CodeLoopStatusModel.DONE -> CODE_LOOP_STATUS_DONE
        CodeLoopStatusModel.FAILED -> CODE_LOOP_STATUS_FAILED
        CodeLoopStatusModel.UNKNOWN -> CODE_LOOP_STATUS_UNKNOWN
    }

private fun CodeLoopFindingModel.toFindingLabel(): String =
    "${severity.toSeverityLabel()}$CODE_LOOP_FINDING_SEPARATOR$file:$line$CODE_LOOP_FINDING_SEPARATOR" +
        "$title$CODE_LOOP_FINDING_FIX_ARROW$fix"

private fun CodeLoopSeverityModel.toSeverityLabel(): String =
    when (this) {
        CodeLoopSeverityModel.CRITICAL -> CODE_LOOP_SEVERITY_LABEL_CRITICAL
        CodeLoopSeverityModel.HIGH -> CODE_LOOP_SEVERITY_LABEL_HIGH
        CodeLoopSeverityModel.MEDIUM -> CODE_LOOP_SEVERITY_LABEL_MEDIUM
        CodeLoopSeverityModel.LOW -> CODE_LOOP_SEVERITY_LABEL_LOW
        CodeLoopSeverityModel.UNKNOWN -> name
    }

private fun CodeLoopRunModel.toCodeLoopSummaryLabel(): String {
    val iterationsLabel = iterationsUsed?.toString() ?: CODE_LOOP_SUMMARY_UNKNOWN
    val findingsBySeverity = events.flatMap { event -> event.findings }
        .groupingBy { finding -> finding.severity }
        .eachCount()
    val severityBreakdown = listOf(
        CodeLoopSeverityModel.CRITICAL,
        CodeLoopSeverityModel.HIGH,
        CodeLoopSeverityModel.MEDIUM,
        CodeLoopSeverityModel.LOW,
    ).joinToString(CODE_LOOP_SUMMARY_SEVERITY_SEPARATOR) { severity ->
        "${severity.toSeverityLabel()}$CODE_LOOP_SUMMARY_SEVERITY_VALUE_SEPARATOR${findingsBySeverity[severity] ?: 0}"
    }
    val findingsTotal = securityFindingsTotal ?: findingsBySeverity.values.sum()
    val gatewayBlocksLabel = gatewayBlocksTotal ?: 0
    return "$CODE_LOOP_SUMMARY_ITERATIONS_PREFIX$iterationsLabel" +
        "$CODE_LOOP_SUMMARY_FINDINGS_PREFIX$findingsTotal ($severityBreakdown)" +
        "$CODE_LOOP_SUMMARY_GATEWAY_PREFIX$gatewayBlocksLabel$CODE_LOOP_SUMMARY_GATEWAY_SUFFIX"
}
