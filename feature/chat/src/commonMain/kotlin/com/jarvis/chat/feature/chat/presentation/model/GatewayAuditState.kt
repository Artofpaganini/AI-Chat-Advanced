package com.jarvis.chat.feature.chat.presentation.model

import com.jarvis.chat.feature.ai.domain.model.GatewayAuditEntryModel
import com.jarvis.chat.feature.ai.domain.model.GatewayLoadErrorModel
import com.jarvis.chat.feature.ai.domain.model.GatewayStatsModel

internal data class GatewayAuditState(
    val isSheetVisible: Boolean = false,
    val isLoading: Boolean = false,
    val entries: List<GatewayAuditEntryModel> = emptyList(),
    val stats: GatewayStatsModel? = null,
    val error: GatewayLoadErrorModel? = null,
)
