package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.FactCheck
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material.icons.filled.FileUpload
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable

private const val SESSIONS_CONTENT_DESCRIPTION = "Open chats"
private const val FAVORITES_CONTENT_DESCRIPTION = "Toggle favorites filter"
private const val EXPORT_CONTENT_DESCRIPTION = "Export chat history"
private const val IMPORT_CONTENT_DESCRIPTION = "Import chat history"
private const val CLEAR_HISTORY_CONTENT_DESCRIPTION = "Clear chat history"
private const val SETTINGS_CONTENT_DESCRIPTION = "Open settings"
private const val GATEWAY_AUDIT_CONTENT_DESCRIPTION = "Open gateway audit log"

@Composable
internal fun ChatTopBarActions(
    isFavoritesFilterActive: Boolean,
    onSessionsClick: () -> Unit,
    onFavoritesClick: () -> Unit,
    onExportClick: () -> Unit,
    onImportClick: () -> Unit,
    onClearHistoryClick: () -> Unit,
    onSettingsClick: () -> Unit,
    onGatewayAuditClick: () -> Unit,
) {
    IconButton(onClick = onSessionsClick) {
        Icon(
            imageVector = Icons.Filled.Forum,
            contentDescription = SESSIONS_CONTENT_DESCRIPTION,
        )
    }
    IconButton(onClick = onFavoritesClick) {
        Icon(
            imageVector = Icons.Filled.Star,
            contentDescription = FAVORITES_CONTENT_DESCRIPTION,
            tint = if (isFavoritesFilterActive) {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.onSurfaceVariant
            },
        )
    }
    IconButton(onClick = onExportClick) {
        Icon(
            imageVector = Icons.Filled.FileUpload,
            contentDescription = EXPORT_CONTENT_DESCRIPTION,
        )
    }
    IconButton(onClick = onImportClick) {
        Icon(
            imageVector = Icons.Filled.FileDownload,
            contentDescription = IMPORT_CONTENT_DESCRIPTION,
        )
    }
    IconButton(onClick = onClearHistoryClick) {
        Icon(
            imageVector = Icons.Filled.Delete,
            contentDescription = CLEAR_HISTORY_CONTENT_DESCRIPTION,
        )
    }
    IconButton(onClick = onGatewayAuditClick) {
        Icon(
            imageVector = Icons.AutoMirrored.Filled.FactCheck,
            contentDescription = GATEWAY_AUDIT_CONTENT_DESCRIPTION,
        )
    }
    IconButton(onClick = onSettingsClick) {
        Icon(
            imageVector = Icons.Filled.Settings,
            contentDescription = SETTINGS_CONTENT_DESCRIPTION,
        )
    }
}
