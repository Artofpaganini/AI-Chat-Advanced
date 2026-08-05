package com.jarvis.chat.feature.chat.presentation

import androidx.lifecycle.viewModelScope
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.ai.domain.model.GatewayLoadErrorModel
import com.jarvis.chat.feature.ai.domain.model.GatewayLoadException
import com.jarvis.chat.feature.ai.domain.usecase.GetGatewayAuditUseCase
import com.jarvis.chat.feature.ai.domain.usecase.GetGatewayStatsUseCase
import com.jarvis.chat.feature.chat.presentation.mapper.GatewayAuditUiMapper
import com.jarvis.chat.feature.chat.presentation.mapper.toGatewayLoadErrorMessage
import com.jarvis.chat.feature.chat.presentation.model.GatewayAuditAction
import com.jarvis.chat.feature.chat.presentation.model.GatewayAuditEvent
import com.jarvis.chat.feature.chat.presentation.model.GatewayAuditState
import com.jarvis.chat.feature.chat.presentation.model.GatewayAuditUiModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

private const val AUDIT_LIMIT = 50

internal class GatewayAuditViewModel(
    private val getGatewayAuditUseCase: GetGatewayAuditUseCase,
    private val getGatewayStatsUseCase: GetGatewayStatsUseCase,
    uiMapper: GatewayAuditUiMapper,
) : UdfBaseViewModel<GatewayAuditAction, GatewayAuditUiModel, GatewayAuditState, GatewayAuditEvent>(
    initialState = GatewayAuditState(),
    uiMapper = uiMapper,
) {

    override fun onAction(action: GatewayAuditAction) {
        when (action) {
            is GatewayAuditAction.Ui.OpenClicked -> onOpenClicked()
            is GatewayAuditAction.Ui.DismissRequested -> onDismissRequested()
            is GatewayAuditAction.Ui.RefreshClicked -> loadAudit()
            is GatewayAuditAction.Internal.Loaded -> onLoaded(action)
            is GatewayAuditAction.Internal.LoadFailed -> onLoadFailed(action)
        }
    }

    private fun onOpenClicked() {
        updateState { copy(isSheetVisible = true) }
        loadAudit()
    }

    private fun onDismissRequested() {
        updateState { copy(isSheetVisible = false) }
    }

    private fun onLoaded(action: GatewayAuditAction.Internal.Loaded) {
        updateState { copy(isLoading = false, entries = action.entries, stats = action.stats, error = null) }
    }

    private fun onLoadFailed(action: GatewayAuditAction.Internal.LoadFailed) {
        updateState { copy(isLoading = false, error = action.error) }
        postEvent(GatewayAuditEvent.ShowMessage(action.error.toGatewayLoadErrorMessage()))
    }

    @Suppress("TooGenericExceptionCaught", "SwallowedException")
    private fun loadAudit() {
        updateState { copy(isLoading = true) }
        viewModelScope.launch {
            try {
                val entries = getGatewayAuditUseCase(AUDIT_LIMIT)
                val stats = getGatewayStatsUseCase()
                onAction(GatewayAuditAction.Internal.Loaded(entries = entries, stats = stats))
            } catch (cancellation: CancellationException) {
                throw cancellation
            } catch (throwable: Throwable) {
                val error = (throwable as? GatewayLoadException)?.error ?: GatewayLoadErrorModel.Unknown
                onAction(GatewayAuditAction.Internal.LoadFailed(error))
            }
        }
    }
}
