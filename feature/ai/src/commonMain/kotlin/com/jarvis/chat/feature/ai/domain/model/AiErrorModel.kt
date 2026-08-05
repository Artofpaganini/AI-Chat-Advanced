package com.jarvis.chat.feature.ai.domain.model

sealed interface AiErrorModel {

    data object NoConnection : AiErrorModel

    data class LocalProviderUnreachable(val address: String) : AiErrorModel

    data object Timeout : AiErrorModel

    data object Unauthorized : AiErrorModel

    data class BadRequest(val message: String) : AiErrorModel

    data class RateLimited(val retryAfterSeconds: Int? = null) : AiErrorModel

    data class ServerError(val code: Int) : AiErrorModel

    data object Unknown : AiErrorModel
}
