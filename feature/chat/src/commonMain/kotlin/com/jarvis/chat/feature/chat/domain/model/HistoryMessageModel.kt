package com.jarvis.chat.feature.chat.domain.model

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.model.MultiStageResultModel
import com.jarvis.chat.feature.ai.domain.model.TriageModel

internal data class HistoryMessageModel(
    val id: String,
    val author: MessageAuthor,
    val text: String,
    val isFavorite: Boolean,
    val timestamp: Long,
    val modelId: String? = null,
    val triage: TriageModel? = null,
    val routeDecision: RouteDecisionModel? = null,
    val multiStage: MultiStageResultModel? = null,
    val inputGuardBlocked: Boolean = false,
    val outputGuardReasons: List<String> = emptyList(),
)
