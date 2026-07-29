package com.jarvis.chat.feature.chat.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TriageDataModel(
    val route: String,
    val routeLabel: String,
    val status: String,
    val statusLabel: String,
    val confidence: Double,
    val explain: String,
    val crisis: Boolean = false,
)
