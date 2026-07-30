package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel
import com.jarvis.chat.feature.chat.presentation.model.ChatSessionItemUiModel
import com.jarvis.chat.feature.chat.presentation.model.SessionsState
import com.jarvis.chat.feature.chat.presentation.model.SessionsUiModel
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime
import kotlin.time.Instant

private const val TIME_LABEL_PAD_LENGTH = 2
private const val TIME_LABEL_PAD_CHAR = '0'
private const val TIME_LABEL_SEPARATOR = ":"
private const val NEW_SESSION_TITLE = "New chat"

internal class SessionsUiMapper : UiMapper<SessionsState, SessionsUiModel> {

    override fun map(state: SessionsState): SessionsUiModel =
        SessionsUiModel(
            sessions = state.sessions
                .sortedByDescending { session -> session.lastMessageAt }
                .map { session -> session.toChatSessionItemUiModel(state.activeSessionId) },
            isSheetVisible = state.isSheetVisible,
            isRenameDialogVisible = state.pendingRenameSessionId != null,
            renameTitle = state.pendingRenameTitle,
            isDeleteConfirmationVisible = state.pendingDeleteSessionId != null,
        )

    private fun ChatSessionModel.toChatSessionItemUiModel(activeSessionId: String): ChatSessionItemUiModel =
        ChatSessionItemUiModel(
            id = id,
            title = title.ifBlank { NEW_SESSION_TITLE },
            lastMessageTimeLabel = lastMessageAt.toTimeLabel(),
            messageCount = messageCount,
            isActive = id == activeSessionId,
        )
}

private fun Long.toTimeLabel(): String {
    val dateTime = Instant.fromEpochMilliseconds(this).toLocalDateTime(TimeZone.currentSystemDefault())
    val hour = dateTime.hour.toString().padStart(TIME_LABEL_PAD_LENGTH, TIME_LABEL_PAD_CHAR)
    val minute = dateTime.minute.toString().padStart(TIME_LABEL_PAD_LENGTH, TIME_LABEL_PAD_CHAR)
    return "$hour$TIME_LABEL_SEPARATOR$minute"
}
