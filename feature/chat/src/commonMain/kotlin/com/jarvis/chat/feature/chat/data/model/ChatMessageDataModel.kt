package com.jarvis.chat.feature.chat.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class ChatMessageDataModel(
    val id: String,
    val author: String,
    val text: String,
    val isFavorite: Boolean,
    val timestamp: Long = 0L,
    val modelId: String? = null,
    val triage: TriageDataModel? = null,
    val isImportedUnverifiedAssistant: Boolean = false,
)
