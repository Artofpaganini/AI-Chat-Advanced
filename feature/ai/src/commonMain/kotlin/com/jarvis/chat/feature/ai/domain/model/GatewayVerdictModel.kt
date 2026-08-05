package com.jarvis.chat.feature.ai.domain.model

enum class GatewayVerdictModel {
    PASS,
    MASKED,
    BLOCKED_INPUT,
    BLOCKED_OUTPUT,
    RATE_LIMITED,
    UNKNOWN,
}
