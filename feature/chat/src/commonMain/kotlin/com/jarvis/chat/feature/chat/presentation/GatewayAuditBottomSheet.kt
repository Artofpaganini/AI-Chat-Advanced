package com.jarvis.chat.feature.chat.presentation

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.jarvis.chat.feature.chat.presentation.model.GatewayAuditAction
import com.jarvis.chat.feature.chat.presentation.model.GatewayAuditEntryUiModel
import org.koin.compose.viewmodel.koinViewModel

private const val TITLE = "Журнал шлюза"
private const val EMPTY_STATE_TEXT = "Записей пока нет"
private const val REFRESH_CONTENT_DESCRIPTION = "Обновить журнал"
private const val COLUMN_TIME_LABEL = "Время"
private const val COLUMN_VERDICT_LABEL = "Вердикт"
private const val COLUMN_REASONS_LABEL = "Причины"
private const val COLUMN_MASKED_LABEL = "Маска"
private const val COLUMN_TOKENS_LABEL = "Токены"
private const val COLUMN_COST_LABEL = "Стоимость"
private const val COLUMN_LATENCY_LABEL = "Задержка"

private val COLUMN_WIDTH_TIME = 120.dp
private val COLUMN_WIDTH_VERDICT = 140.dp
private val COLUMN_WIDTH_REASONS = 220.dp
private val COLUMN_WIDTH_MASKED = 80.dp
private val COLUMN_WIDTH_TOKENS = 140.dp
private val COLUMN_WIDTH_COST = 100.dp
private val COLUMN_WIDTH_LATENCY = 100.dp
private val SPACING_XS = 8.dp
private val SPACING_SM = 12.dp
private val SPACING_MD = 16.dp
private val CELL_HORIZONTAL_PADDING = 4.dp
private val GATEWAY_AUDIT_LIST_HEIGHT = 360.dp

@Composable
fun rememberOpenGatewayAuditAction(): () -> Unit {
    val viewModel: GatewayAuditViewModel = koinViewModel()
    return remember(viewModel) { { viewModel.onAction(GatewayAuditAction.Ui.OpenClicked) } }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GatewayAuditBottomSheet() {
    val viewModel: GatewayAuditViewModel = koinViewModel()
    val uiState by viewModel.uiState.collectAsState()

    if (uiState.isSheetVisible) {
        ModalBottomSheet(onDismissRequest = { viewModel.onAction(GatewayAuditAction.Ui.DismissRequested) }) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(SPACING_MD)
                    .navigationBarsPadding(),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = TITLE,
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.weight(1f),
                    )
                    IconButton(onClick = { viewModel.onAction(GatewayAuditAction.Ui.RefreshClicked) }) {
                        Icon(imageVector = Icons.Filled.Refresh, contentDescription = REFRESH_CONTENT_DESCRIPTION)
                    }
                }
                uiState.statsSummary?.let { statsSummary ->
                    Spacer(modifier = Modifier.height(SPACING_XS))
                    Text(text = statsSummary.totalRequestsLabel, style = MaterialTheme.typography.bodySmall)
                    Text(text = statsSummary.blockedLabel, style = MaterialTheme.typography.bodySmall)
                    Text(text = statsSummary.maskedLabel, style = MaterialTheme.typography.bodySmall)
                    Text(text = statsSummary.rateLimitedLabel, style = MaterialTheme.typography.bodySmall)
                    Text(text = statsSummary.tokensLabel, style = MaterialTheme.typography.bodySmall)
                    Text(text = statsSummary.costLabel, style = MaterialTheme.typography.bodySmall)
                }
                Spacer(modifier = Modifier.height(SPACING_SM))
                uiState.errorMessage?.let { errorMessage ->
                    Text(text = errorMessage, color = MaterialTheme.colorScheme.error)
                    Spacer(modifier = Modifier.height(SPACING_SM))
                }
                if (uiState.isLoading) {
                    CircularProgressIndicator(modifier = Modifier.padding(SPACING_MD))
                } else if (uiState.isEmptyState) {
                    Text(text = EMPTY_STATE_TEXT, style = MaterialTheme.typography.bodyMedium)
                } else {
                    GatewayAuditTable(entries = uiState.entries)
                }
            }
        }
    }
}

@Composable
private fun GatewayAuditTable(entries: List<GatewayAuditEntryUiModel>, modifier: Modifier = Modifier) {
    val scrollState = rememberScrollState()
    Column(modifier = modifier.horizontalScroll(scrollState)) {
        GatewayAuditHeaderRow()
        HorizontalDivider()
        LazyColumn(modifier = Modifier.height(GATEWAY_AUDIT_LIST_HEIGHT)) {
            items(items = entries, key = { entry -> entry.requestId }) { entry ->
                GatewayAuditRow(entry = entry)
                HorizontalDivider()
            }
        }
    }
}

@Composable
private fun GatewayAuditHeaderRow(modifier: Modifier = Modifier) {
    Row(modifier = modifier.padding(vertical = SPACING_XS)) {
        TableCell(text = COLUMN_TIME_LABEL, width = COLUMN_WIDTH_TIME, style = MaterialTheme.typography.labelMedium)
        TableCell(text = COLUMN_VERDICT_LABEL, width = COLUMN_WIDTH_VERDICT, style = MaterialTheme.typography.labelMedium)
        TableCell(text = COLUMN_REASONS_LABEL, width = COLUMN_WIDTH_REASONS, style = MaterialTheme.typography.labelMedium)
        TableCell(text = COLUMN_MASKED_LABEL, width = COLUMN_WIDTH_MASKED, style = MaterialTheme.typography.labelMedium)
        TableCell(text = COLUMN_TOKENS_LABEL, width = COLUMN_WIDTH_TOKENS, style = MaterialTheme.typography.labelMedium)
        TableCell(text = COLUMN_COST_LABEL, width = COLUMN_WIDTH_COST, style = MaterialTheme.typography.labelMedium)
        TableCell(text = COLUMN_LATENCY_LABEL, width = COLUMN_WIDTH_LATENCY, style = MaterialTheme.typography.labelMedium)
    }
}

@Composable
private fun GatewayAuditRow(entry: GatewayAuditEntryUiModel, modifier: Modifier = Modifier) {
    Row(modifier = modifier.padding(vertical = SPACING_XS)) {
        TableCell(text = entry.timeLabel, width = COLUMN_WIDTH_TIME, style = MaterialTheme.typography.bodySmall)
        TableCell(text = entry.verdictLabel, width = COLUMN_WIDTH_VERDICT, style = MaterialTheme.typography.bodySmall)
        TableCell(text = entry.reasonsLabel, width = COLUMN_WIDTH_REASONS, style = MaterialTheme.typography.bodySmall)
        TableCell(text = entry.maskedCount.toString(), width = COLUMN_WIDTH_MASKED, style = MaterialTheme.typography.bodySmall)
        TableCell(text = entry.tokensLabel, width = COLUMN_WIDTH_TOKENS, style = MaterialTheme.typography.bodySmall)
        TableCell(text = entry.costLabel, width = COLUMN_WIDTH_COST, style = MaterialTheme.typography.bodySmall)
        TableCell(text = entry.latencyLabel, width = COLUMN_WIDTH_LATENCY, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun TableCell(text: String, width: Dp, style: TextStyle, modifier: Modifier = Modifier) {
    Text(
        text = text,
        style = style,
        maxLines = 2,
        modifier = modifier.width(width).padding(horizontal = CELL_HORIZONTAL_PADDING),
    )
}
