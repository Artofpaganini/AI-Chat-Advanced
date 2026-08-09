package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.domain.model.CodeLoopErrorModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageEventModel
import io.ktor.client.plugins.ClientRequestException
import io.ktor.client.plugins.ServerResponseException
import io.ktor.serialization.JsonConvertException
import kotlinx.io.IOException
import kotlinx.serialization.SerializationException

internal fun Throwable.toCodeLoopErrorModel(
    rootUrl: String,
    lastEvent: CodeLoopStageEventModel?,
): CodeLoopErrorModel =
    when (this) {
        is SerializationException -> CodeLoopErrorModel.MalformedResponse(detail = message.orEmpty())
        is JsonConvertException -> CodeLoopErrorModel.MalformedResponse(detail = message.orEmpty())
        is ClientRequestException -> CodeLoopErrorModel.MalformedResponse(detail = "HTTP ${response.status.value}")
        is ServerResponseException -> CodeLoopErrorModel.MalformedResponse(detail = "HTTP ${response.status.value}")
        is IOException -> if (lastEvent == null) {
            CodeLoopErrorModel.ServerUnavailable(address = rootUrl)
        } else {
            CodeLoopErrorModel.InterruptedMidRun(lastStage = lastEvent.stage, lastIteration = lastEvent.iteration)
        }
        else -> CodeLoopErrorModel.MalformedResponse(detail = message.orEmpty())
    }
