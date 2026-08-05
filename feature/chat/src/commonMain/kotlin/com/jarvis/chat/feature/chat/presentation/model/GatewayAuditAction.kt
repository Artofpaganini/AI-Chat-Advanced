package com.jarvis.chat.feature.chat.presentation.model

import com.jarvis.chat.feature.ai.domain.model.GatewayAuditEntryModel
import com.jarvis.chat.feature.ai.domain.model.GatewayLoadErrorModel
import com.jarvis.chat.feature.ai.domain.model.GatewayStatsModel

internal sealed interface GatewayAuditAction {

    sealed interface Ui : GatewayAuditAction {

        data object OpenClicked : Ui

        data object DismissRequested : Ui

        data object RefreshClicked : Ui
    }

    sealed interface Internal : GatewayAuditAction {

        data class Loaded(val entries: List<GatewayAuditEntryModel>, val stats: GatewayStatsModel) : Internal

        data class LoadFailed(val error: GatewayLoadErrorModel) : Internal
    }
}
