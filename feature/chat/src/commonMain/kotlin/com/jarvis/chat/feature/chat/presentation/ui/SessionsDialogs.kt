package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable

private const val RENAME_SESSION_DIALOG_TITLE = "Rename chat"
private const val RENAME_SESSION_CONFIRM_BUTTON = "Save"
private const val RENAME_SESSION_DISMISS_BUTTON = "Cancel"
private const val DELETE_SESSION_DIALOG_TITLE = "Delete chat?"
private const val DELETE_SESSION_DIALOG_TEXT = "This will permanently delete this chat and all its messages. This action cannot be undone."
private const val DELETE_SESSION_CONFIRM_BUTTON = "Delete"
private const val DELETE_SESSION_DISMISS_BUTTON = "Cancel"

@Composable
internal fun RenameSessionDialog(
    title: String,
    onTitleChange: (String) -> Unit,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(text = RENAME_SESSION_DIALOG_TITLE) },
        text = {
            OutlinedTextField(
                value = title,
                onValueChange = onTitleChange,
                singleLine = true,
            )
        },
        confirmButton = {
            TextButton(onClick = onConfirm) {
                Text(text = RENAME_SESSION_CONFIRM_BUTTON)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(text = RENAME_SESSION_DISMISS_BUTTON)
            }
        },
    )
}

@Composable
internal fun DeleteSessionConfirmationDialog(
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(text = DELETE_SESSION_DIALOG_TITLE) },
        text = { Text(text = DELETE_SESSION_DIALOG_TEXT) },
        confirmButton = {
            TextButton(onClick = onConfirm) {
                Text(text = DELETE_SESSION_CONFIRM_BUTTON)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(text = DELETE_SESSION_DISMISS_BUTTON)
            }
        },
    )
}
