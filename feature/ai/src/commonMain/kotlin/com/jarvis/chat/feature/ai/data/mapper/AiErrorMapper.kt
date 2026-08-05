package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigModel
import io.ktor.client.plugins.ClientRequestException
import io.ktor.client.plugins.HttpRequestTimeoutException
import io.ktor.client.plugins.ServerResponseException
import io.ktor.client.statement.bodyAsText
import kotlinx.io.IOException

private const val HTTP_STATUS_BAD_REQUEST = 400
private const val HTTP_STATUS_UNAUTHORIZED = 401
private const val HTTP_STATUS_TOO_MANY_REQUESTS = 429
private const val HEADER_RETRY_AFTER = "Retry-After"

private val CLOUD_LIKE_PROVIDER_CONFIG = AiProviderConfigModel(
    baseUrl = "",
    modelId = "",
    systemPrompt = "",
    isApiKeyRequired = true,
)

internal suspend fun Throwable.toAiErrorModel(
    providerConfig: AiProviderConfigModel = CLOUD_LIKE_PROVIDER_CONFIG,
): AiErrorModel = when (this) {
    is HttpRequestTimeoutException -> AiErrorModel.Timeout
    is ClientRequestException -> toClientRequestAiErrorModel()
    is ServerResponseException -> AiErrorModel.ServerError(code = response.status.value)
    is IOException -> if (providerConfig.isApiKeyRequired) {
        AiErrorModel.NoConnection
    } else {
        AiErrorModel.LocalProviderUnreachable(address = providerConfig.baseUrl)
    }
    else -> AiErrorModel.Unknown
}

private suspend fun ClientRequestException.toClientRequestAiErrorModel(): AiErrorModel =
    when (response.status.value) {
        HTTP_STATUS_UNAUTHORIZED -> AiErrorModel.Unauthorized
        HTTP_STATUS_TOO_MANY_REQUESTS ->
            AiErrorModel.RateLimited(retryAfterSeconds = response.headers[HEADER_RETRY_AFTER]?.toIntOrNull())
        HTTP_STATUS_BAD_REQUEST -> AiErrorModel.BadRequest(message = badRequestMessage())
        else -> AiErrorModel.Unknown
    }

private suspend fun ClientRequestException.badRequestMessage(): String =
    runCatching { response.bodyAsText() }
        .getOrNull()
        ?.takeIf { text -> text.isNotBlank() }
        ?: message.orEmpty()
