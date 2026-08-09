package com.jarvis.chat.feature.chat.domain.mapper

import com.jarvis.chat.feature.ai.domain.model.CodeLoopErrorModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopRunModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageModel

private const val CODE_LOOP_COMMIT_PREFIX = "Цикл завершён коммитом "
private const val CODE_LOOP_NO_COMMIT_PREFIX = "Цикл остановился без коммита на стадии "
private const val CODE_LOOP_STAGE_UNKNOWN = "неизвестной стадии"
private const val CODE_LOOP_ITERATION_PREFIX = ", итерация "
private const val CODE_LOOP_SERVER_UNAVAILABLE_PREFIX = "Сервер цикла не запущен или недоступен по адресу "
private const val CODE_LOOP_MALFORMED_PREFIX = "Сервер цикла ответил в неожиданном формате: "
private const val CODE_LOOP_INTERRUPTED_PREFIX = "Цикл прервался на середине на стадии "
private const val CODE_LOOP_NO_FILES_TEXT = "Код не получен."
private const val CODE_LANGUAGE_KOTLIN = "kotlin"
private const val CODE_BLOCK_TITLE_SEPARATOR = "\n"
private const val CODE_BLOCK_SEPARATOR = "\n\n"
private const val TEXT_SEPARATOR = "\n\n"

internal fun CodeLoopRunModel.toReplyText(): String {
    val runError = error
    if (runError != null) {
        return runError.toErrorText()
    }
    val codeBlocksText = finalCode.toCodeBlocksText()
    return if (commit != null) {
        "$CODE_LOOP_COMMIT_PREFIX$commit$TEXT_SEPARATOR$codeBlocksText"
    } else {
        "$CODE_LOOP_NO_COMMIT_PREFIX${lastStageLabel()}$TEXT_SEPARATOR$codeBlocksText"
    }
}

private fun CodeLoopRunModel.lastStageLabel(): String {
    val lastEvent = events.lastOrNull { event -> event.stage != CodeLoopStageModel.RESULT }
        ?: return CODE_LOOP_STAGE_UNKNOWN
    val iterationSuffix = lastEvent.iteration?.let { iteration -> "$CODE_LOOP_ITERATION_PREFIX$iteration" }.orEmpty()
    return "${lastEvent.stage.name}$iterationSuffix"
}

private fun Map<String, String>.toCodeBlocksText(): String =
    if (isEmpty()) {
        CODE_LOOP_NO_FILES_TEXT
    } else {
        entries.joinToString(separator = CODE_BLOCK_SEPARATOR) { (fileName, content) ->
            "$fileName$CODE_BLOCK_TITLE_SEPARATOR```$CODE_LANGUAGE_KOTLIN\n$content\n```"
        }
    }

private fun CodeLoopErrorModel.toErrorText(): String =
    when (this) {
        is CodeLoopErrorModel.ServerUnavailable -> "$CODE_LOOP_SERVER_UNAVAILABLE_PREFIX$address"
        is CodeLoopErrorModel.MalformedResponse -> "$CODE_LOOP_MALFORMED_PREFIX$detail"
        is CodeLoopErrorModel.InterruptedMidRun -> {
            val stageLabel = lastStage?.name ?: CODE_LOOP_STAGE_UNKNOWN
            val iterationSuffix = lastIteration?.let { iteration -> "$CODE_LOOP_ITERATION_PREFIX$iteration" }.orEmpty()
            "$CODE_LOOP_INTERRUPTED_PREFIX$stageLabel$iterationSuffix"
        }
    }
