package com.jarvis.chat.feature.chat.presentation.model

internal sealed interface GatewayAuditEvent {

    data class ShowMessage(val text: String) : GatewayAuditEvent
}
