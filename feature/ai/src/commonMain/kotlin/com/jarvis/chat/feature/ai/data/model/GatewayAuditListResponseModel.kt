package com.jarvis.chat.feature.ai.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class GatewayAuditListResponseModel(
    val items: List<GatewayAuditEntryResponseModel> = emptyList(),
    val count: Int = 0,
)
