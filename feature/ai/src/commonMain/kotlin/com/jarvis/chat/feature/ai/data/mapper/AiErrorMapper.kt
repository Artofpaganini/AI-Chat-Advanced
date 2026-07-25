package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import io.ktor.client.plugins.ClientRequestException
import io.ktor.client.plugins.HttpRequestTimeoutException
import io.ktor.client.plugins.ServerResponseException
import io.ktor.client.statement.bodyAsText
import kotlinx.io.IOException

private const val HTTP_STATUS_BAD_REQUEST = 400
private const val HTTP_STATUS_UNAUTHORIZED = 401
private const val HTTP_STATUS_TOO_MANY_REQUESTS = 429

internal suspend fun Throwable.toAiErrorModel(): AiErrorModel = when (this) {
    is HttpRequestTimeoutException -> AiErrorModel.Timeout
    is ClientRequestException -> toClientRequestAiErrorModel()
    is ServerResponseException -> AiErrorModel.ServerError(code = response.status.value)
    is IOException -> AiErrorModel.NoConnection
    else -> AiErrorModel.Unknown
}

private suspend fun ClientRequestException.toClientRequestAiErrorModel(): AiErrorModel =
    when (response.status.value) {
        HTTP_STATUS_UNAUTHORIZED -> AiErrorModel.Unauthorized
        HTTP_STATUS_TOO_MANY_REQUESTS -> AiErrorModel.RateLimited
        HTTP_STATUS_BAD_REQUEST -> AiErrorModel.BadRequest(message = badRequestMessage())
        else -> AiErrorModel.Unknown
    }

private suspend fun ClientRequestException.badRequestMessage(): String =
    runCatching { response.bodyAsText() }
        .getOrNull()
        ?.takeIf { text -> text.isNotBlank() }
        ?: message.orEmpty()
