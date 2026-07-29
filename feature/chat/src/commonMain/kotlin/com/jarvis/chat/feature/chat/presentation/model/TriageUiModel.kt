package com.jarvis.chat.feature.chat.presentation.model

internal data class TriageUiModel(
    val route: TriageRouteUiModel,
    val routeLabel: String,
    val status: TriageStatusUiModel,
    val statusLabel: String,
    val confidencePercent: Int,
    val explain: String,
    val crisis: Boolean,
)
