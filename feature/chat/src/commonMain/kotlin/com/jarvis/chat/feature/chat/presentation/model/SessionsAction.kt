package com.jarvis.chat.feature.chat.presentation.model

import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel

internal sealed interface SessionsAction {

    sealed interface Ui : SessionsAction {

        data object OpenClicked : Ui

        data object DismissRequested : Ui

        data object CreateClicked : Ui

        data class SessionClicked(val sessionId: String) : Ui

        data class RenameClicked(val sessionId: String) : Ui

        data class RenameTitleChanged(val title: String) : Ui

        data object RenameConfirmed : Ui

        data object RenameCancelled : Ui

        data class DeleteClicked(val sessionId: String) : Ui

        data object DeleteConfirmed : Ui

        data object DeleteCancelled : Ui
    }

    sealed interface Internal : SessionsAction {

        data class SessionsLoaded(val sessions: List<ChatSessionModel>, val activeSessionId: String) : Internal

        data class SessionCreated(val sessions: List<ChatSessionModel>, val activeSessionId: String) : Internal

        data class SessionDeleted(val sessions: List<ChatSessionModel>, val activeSessionId: String) : Internal

        data object OperationFailed : Internal
    }
}
