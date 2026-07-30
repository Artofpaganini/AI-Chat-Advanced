package com.jarvis.chat.feature.chat.presentation

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import com.jarvis.chat.feature.chat.presentation.model.ChatSessionItemUiModel
import com.jarvis.chat.feature.chat.presentation.model.SessionsAction
import com.jarvis.chat.feature.chat.presentation.ui.ChatDimens
import com.jarvis.chat.feature.chat.presentation.ui.DeleteSessionConfirmationDialog
import com.jarvis.chat.feature.chat.presentation.ui.RenameSessionDialog
import org.koin.compose.viewmodel.koinViewModel

private const val SESSIONS_TITLE = "Chats"
private const val NEW_SESSION_LABEL = "New chat"
private const val RENAME_CONTENT_DESCRIPTION = "Rename chat"
private const val DELETE_CONTENT_DESCRIPTION = "Delete chat"
private const val MESSAGE_COUNT_SEPARATOR = " · "
private const val MESSAGE_COUNT_SUFFIX = " messages"

@Composable
fun rememberOpenSessionsAction(): () -> Unit {
    val viewModel: SessionsViewModel = koinViewModel()
    return remember(viewModel) { { viewModel.onAction(SessionsAction.Ui.OpenClicked) } }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SessionsBottomSheet() {
    val viewModel: SessionsViewModel = koinViewModel()
    val uiState by viewModel.uiState.collectAsState()

    if (uiState.isSheetVisible) {
        ModalBottomSheet(onDismissRequest = { viewModel.onAction(SessionsAction.Ui.DismissRequested) }) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(ChatDimens.spacingMd)
                    .navigationBarsPadding(),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = SESSIONS_TITLE,
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.weight(1f),
                    )
                    TextButton(onClick = { viewModel.onAction(SessionsAction.Ui.CreateClicked) }) {
                        Icon(imageVector = Icons.Filled.Add, contentDescription = null)
                        Text(text = NEW_SESSION_LABEL)
                    }
                }
                Spacer(modifier = Modifier.height(ChatDimens.spacingSm))
                LazyColumn {
                    items(uiState.sessions) { session ->
                        SessionRow(
                            session = session,
                            onSessionClick = { viewModel.onAction(SessionsAction.Ui.SessionClicked(session.id)) },
                            onRenameClick = { viewModel.onAction(SessionsAction.Ui.RenameClicked(session.id)) },
                            onDeleteClick = { viewModel.onAction(SessionsAction.Ui.DeleteClicked(session.id)) },
                        )
                    }
                }
            }
        }
    }

    if (uiState.isRenameDialogVisible) {
        RenameSessionDialog(
            title = uiState.renameTitle,
            onTitleChange = { title -> viewModel.onAction(SessionsAction.Ui.RenameTitleChanged(title)) },
            onConfirm = { viewModel.onAction(SessionsAction.Ui.RenameConfirmed) },
            onDismiss = { viewModel.onAction(SessionsAction.Ui.RenameCancelled) },
        )
    }

    if (uiState.isDeleteConfirmationVisible) {
        DeleteSessionConfirmationDialog(
            onConfirm = { viewModel.onAction(SessionsAction.Ui.DeleteConfirmed) },
            onDismiss = { viewModel.onAction(SessionsAction.Ui.DeleteCancelled) },
        )
    }
}

@Composable
private fun SessionRow(
    session: ChatSessionItemUiModel,
    onSessionClick: () -> Unit,
    onRenameClick: () -> Unit,
    onDeleteClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onSessionClick)
            .padding(vertical = ChatDimens.spacingXs),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = session.title,
                style = MaterialTheme.typography.bodyLarge,
                color = if (session.isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = "${session.lastMessageTimeLabel}$MESSAGE_COUNT_SEPARATOR${session.messageCount}$MESSAGE_COUNT_SUFFIX",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        IconButton(onClick = onRenameClick) {
            Icon(imageVector = Icons.Filled.Edit, contentDescription = RENAME_CONTENT_DESCRIPTION)
        }
        IconButton(onClick = onDeleteClick) {
            Icon(imageVector = Icons.Filled.Delete, contentDescription = DELETE_CONTENT_DESCRIPTION)
        }
    }
}
