package com.jarvis.chat.feature.chat.presentation.model

internal data class GatewaySignalUiModel(
    val isBannerVisible: Boolean,
    val bannerText: String,
    val costTokensLabel: String,
    val shortVerdictLabel: String?,
    val isShortVerdictWarning: Boolean,
)
