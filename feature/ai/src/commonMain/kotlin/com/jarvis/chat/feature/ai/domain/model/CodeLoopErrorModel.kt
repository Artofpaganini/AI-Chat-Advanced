package com.jarvis.chat.feature.ai.domain.model

sealed interface CodeLoopErrorModel {

    data class ServerUnavailable(val address: String) : CodeLoopErrorModel

    data class MalformedResponse(val detail: String) : CodeLoopErrorModel

    data class InterruptedMidRun(val lastStage: CodeLoopStageModel?, val lastIteration: Int?) : CodeLoopErrorModel
}
