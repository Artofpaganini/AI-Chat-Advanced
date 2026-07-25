package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable

private const val CLEAR_HISTORY_DIALOG_TITLE = "Clear chat history?"
private const val CLEAR_HISTORY_DIALOG_TEXT = "This will permanently delete all messages. This action cannot be undone."
private const val CLEAR_HISTORY_CONFIRM_BUTTON = "Clear"
private const val CLEAR_HISTORY_DISMISS_BUTTON = "Cancel"
private const val DELETE_MESSAGE_DIALOG_TITLE = "Delete message?"
private const val DELETE_MESSAGE_DIALOG_TEXT = "This will permanently delete this message. This action cannot be undone."
private const val DELETE_MESSAGE_CONFIRM_BUTTON = "Delete"
private const val DELETE_MESSAGE_DISMISS_BUTTON = "Cancel"

@Composable
internal fun ClearHistoryConfirmationDialog(
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(text = CLEAR_HISTORY_DIALOG_TITLE) },
        text = { Text(text = CLEAR_HISTORY_DIALOG_TEXT) },
        confirmButton = {
            TextButton(onClick = onConfirm) {
                Text(text = CLEAR_HISTORY_CONFIRM_BUTTON)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(text = CLEAR_HISTORY_DISMISS_BUTTON)
            }
        },
    )
}

@Composable
internal fun DeleteMessageConfirmationDialog(
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(text = DELETE_MESSAGE_DIALOG_TITLE) },
        text = { Text(text = DELETE_MESSAGE_DIALOG_TEXT) },
        confirmButton = {
            TextButton(onClick = onConfirm) {
                Text(text = DELETE_MESSAGE_CONFIRM_BUTTON)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text(text = DELETE_MESSAGE_DISMISS_BUTTON)
            }
        },
    )
}
