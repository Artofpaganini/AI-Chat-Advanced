package com.jarvis.chat.feature.chat.presentation.model

internal data class SessionsUiModel(
    val sessions: List<ChatSessionItemUiModel>,
    val isSheetVisible: Boolean,
    val isRenameDialogVisible: Boolean,
    val renameTitle: String,
    val isDeleteConfirmationVisible: Boolean,
)
