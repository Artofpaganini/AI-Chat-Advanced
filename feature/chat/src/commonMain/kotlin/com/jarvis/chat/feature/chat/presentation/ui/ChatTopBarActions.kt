package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material.icons.filled.FileUpload
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable

private const val FAVORITES_CONTENT_DESCRIPTION = "Toggle favorites filter"
private const val EXPORT_CONTENT_DESCRIPTION = "Export chat history"
private const val IMPORT_CONTENT_DESCRIPTION = "Import chat history"
private const val CLEAR_HISTORY_CONTENT_DESCRIPTION = "Clear chat history"
private const val SETTINGS_CONTENT_DESCRIPTION = "Open settings"

@Composable
internal fun ChatTopBarActions(
    isFavoritesFilterActive: Boolean,
    onFavoritesClick: () -> Unit,
    onExportClick: () -> Unit,
    onImportClick: () -> Unit,
    onClearHistoryClick: () -> Unit,
    onSettingsClick: () -> Unit,
) {
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
    IconButton(onClick = onSettingsClick) {
        Icon(
            imageVector = Icons.Filled.Settings,
            contentDescription = SETTINGS_CONTENT_DESCRIPTION,
        )
    }
}
