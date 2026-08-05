package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.domain.model.GatewayLoadErrorModel
import io.ktor.serialization.JsonConvertException
import kotlinx.io.IOException
import kotlinx.serialization.SerializationException

internal fun Throwable.toGatewayLoadErrorModel(): GatewayLoadErrorModel =
    when (this) {
        is JsonConvertException -> GatewayLoadErrorModel.ParseFailed
        is SerializationException -> GatewayLoadErrorModel.ParseFailed
        is IOException -> GatewayLoadErrorModel.NoConnection
        else -> GatewayLoadErrorModel.Unknown
    }
