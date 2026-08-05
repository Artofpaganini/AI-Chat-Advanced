package com.jarvis.chat.feature.ai.domain.model

sealed interface GatewayLoadErrorModel {

    data object NoConnection : GatewayLoadErrorModel

    data object ParseFailed : GatewayLoadErrorModel

    data object Unknown : GatewayLoadErrorModel
}
