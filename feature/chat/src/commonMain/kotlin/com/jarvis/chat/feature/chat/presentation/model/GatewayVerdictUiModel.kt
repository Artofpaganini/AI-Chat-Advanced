package com.jarvis.chat.feature.chat.presentation.model

internal enum class GatewayVerdictUiModel {
    PASS,
    MASKED,
    BLOCKED_INPUT,
    BLOCKED_OUTPUT,
    RATE_LIMITED,
    UNKNOWN,
}
