package com.jarvis.chat.feature.ai.domain.mapper

import com.jarvis.chat.feature.ai.domain.model.CodeLoopErrorModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopRunModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageEventModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStatusModel

fun List<CodeLoopStageEventModel>.toCodeLoopRunModel(
    task: String,
    error: CodeLoopErrorModel? = null,
): CodeLoopRunModel {
    val resultEvent = lastOrNull { event -> event.stage == CodeLoopStageModel.RESULT }
    val commitEvent = lastOrNull { event ->
        event.stage == CodeLoopStageModel.COMMIT && event.status == CodeLoopStatusModel.DONE
    }
    return CodeLoopRunModel(
        task = task,
        events = toList(),
        isRunning = error == null && resultEvent == null,
        commit = commitEvent?.commit,
        iterationsUsed = resultEvent?.iterationsUsed,
        securityFindingsTotal = resultEvent?.securityFindings,
        gatewayBlocksTotal = resultEvent?.gatewayBlocks,
        finalCode = resultEvent?.finalCode.orEmpty(),
        error = error,
    )
}
