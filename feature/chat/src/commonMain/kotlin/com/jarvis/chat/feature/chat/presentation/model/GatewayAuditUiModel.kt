package com.jarvis.chat.feature.chat.presentation.model

internal data class GatewayAuditUiModel(
    val isSheetVisible: Boolean,
    val isLoading: Boolean,
    val entries: List<GatewayAuditEntryUiModel>,
    val statsSummary: GatewayStatsUiModel?,
    val isEmptyState: Boolean,
    val errorMessage: String?,
)

internal data class GatewayAuditEntryUiModel(
    val requestId: String,
    val timeLabel: String,
    val verdictLabel: String,
    val reasonsLabel: String,
    val maskedCount: Int,
    val tokensLabel: String,
    val costLabel: String,
    val latencyLabel: String,
)

internal data class GatewayStatsUiModel(
    val totalRequestsLabel: String,
    val blockedLabel: String,
    val maskedLabel: String,
    val rateLimitedLabel: String,
    val tokensLabel: String,
    val costLabel: String,
)
