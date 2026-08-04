package com.jarvis.chat.feature.chat.domain.model

internal data class ImportOutcomeModel(
    val messages: List<HistoryMessageModel>,
    val acceptedCount: Int,
    val droppedCount: Int,
    val truncatedCount: Int,
    val dropReasons: List<ImportRejectionReasonModel>,
    val fileRejected: Boolean,
    val fileRejectionReason: ImportRejectionReasonModel? = null,
)
