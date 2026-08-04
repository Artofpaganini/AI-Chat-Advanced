package com.jarvis.chat.feature.chat.data.mapper

import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.data.model.ChatMessageDataModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel

private const val AUTHOR_ASSISTANT = "ASSISTANT"

internal fun ChatMessageDataModel.toHistoryMessageModel(isImported: Boolean = false): HistoryMessageModel =
    HistoryMessageModel(
        id = id,
        author = if (author == AUTHOR_ASSISTANT) MessageAuthor.ASSISTANT else MessageAuthor.USER,
        text = text,
        isFavorite = isFavorite,
        timestamp = timestamp,
        modelId = modelId,
        triage = triage?.toTriageModel(),
        isImportedUnverifiedAssistant = author == AUTHOR_ASSISTANT && (isImported || isImportedUnverifiedAssistant),
    )
