package com.jarvis.chat.feature.chat.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material.icons.filled.FileUpload
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import com.jarvis.chat.feature.chat.presentation.model.ChatEvent
import com.jarvis.chat.feature.chat.presentation.model.ChatUiModel
import com.jarvis.chat.feature.chat.presentation.ui.ChatDimens
import com.jarvis.chat.feature.chat.presentation.ui.MessageBubble
import com.jarvis.chat.feature.chat.presentation.ui.MessageInputBar
import com.jarvis.chat.feature.chat.presentation.ui.TypingIndicator
import com.jarvis.chat.feature.chat.resources.Res
import com.jarvis.chat.feature.voice.model.SpeechRecognitionStateModel
import com.jarvis.chat.feature.voice.rememberSpeechRecognitionController
import kotlinx.coroutines.launch
import nl.marc_apps.tts.rememberTextToSpeechOrNull
import org.koin.compose.viewmodel.koinViewModel

private const val TITLE = "Jarvis"
private const val EMPTY_HINT = "Ask Jarvis anything to start the conversation."
private const val EMPTY_FAVORITES_HINT = "No favorites yet. Tap the star icon on an answer to save it."
private const val ERROR_MESSAGE = "Something went wrong. Please try again."
private const val RETRY_BUTTON_TEXT = "Retry"
private const val FAVORITES_CONTENT_DESCRIPTION = "Toggle favorites filter"
private const val EXPORT_CONTENT_DESCRIPTION = "Export chat history"
private const val IMPORT_CONTENT_DESCRIPTION = "Import chat history"
private const val CLEAR_HISTORY_CONTENT_DESCRIPTION = "Clear chat history"
private const val CLEAR_HISTORY_DIALOG_TITLE = "Clear chat history?"
private const val CLEAR_HISTORY_DIALOG_TEXT = "This will permanently delete all messages. This action cannot be undone."
private const val CLEAR_HISTORY_CONFIRM_BUTTON = "Clear"
private const val CLEAR_HISTORY_DISMISS_BUTTON = "Cancel"
private const val MOCK_HISTORY_PATH = "files/mock_chat_history.json"

@Composable
fun ChatScreen(modifier: Modifier = Modifier) {
    ChatContent(modifier = modifier)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun ChatContent(
    modifier: Modifier = Modifier,
    viewModel: ChatViewModel = koinViewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()
    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()
    val snackbarHostState = remember { SnackbarHostState() }
    val textToSpeech = rememberTextToSpeechOrNull()
    val isTtsAvailable = textToSpeech != null
    val speechRecognitionController = rememberSpeechRecognitionController(
        onTranscript = { text -> viewModel.onAction(ChatAction.Ui.VoiceTranscribed(text)) },
    )
    val recognitionState by speechRecognitionController.state.collectAsState()
    val isListening = recognitionState is SpeechRecognitionStateModel.Listening

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                ChatEvent.ScrollToBottom -> {
                    val lastIndex = (listState.layoutInfo.totalItemsCount - 1).coerceAtLeast(0)
                    listState.animateScrollToItem(lastIndex)
                }

                is ChatEvent.ShowMessage -> snackbarHostState.showSnackbar(event.text)
            }
        }
    }

    if (uiState.showClearConfirmation) {
        ClearHistoryConfirmationDialog(
            onConfirm = { viewModel.onAction(ChatAction.Ui.ClearHistoryConfirmed) },
            onDismiss = { viewModel.onAction(ChatAction.Ui.ClearHistoryCancelled) },
        )
    }

    Scaffold(
        modifier = modifier,
        topBar = {
            TopAppBar(
                title = { Text(text = TITLE) },
                actions = {
                    ChatTopBarActions(
                        isFavoritesFilterActive = uiState.isFavoritesFilterActive,
                        onFavoritesClick = { viewModel.onAction(ChatAction.Ui.FavoritesFilterToggled) },
                        onExportClick = { viewModel.onAction(ChatAction.Ui.ExportClicked) },
                        onImportClick = {
                            coroutineScope.launch {
                                runCatching { Res.readBytes(MOCK_HISTORY_PATH).decodeToString() }
                                    .onSuccess { json -> viewModel.onAction(ChatAction.Ui.ImportRequested(json)) }
                            }
                        },
                        onClearHistoryClick = { viewModel.onAction(ChatAction.Ui.ClearHistoryClicked) },
                    )
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            MessageInputBar(
                inputText = uiState.inputText,
                isSendEnabled = uiState.isSendEnabled,
                isListening = isListening,
                onInputChange = { text -> viewModel.onAction(ChatAction.Ui.InputChanged(text)) },
                onSendClick = { viewModel.onAction(ChatAction.Ui.SendClicked) },
                onMicClick = { speechRecognitionController.toggle() },
                modifier = Modifier
                    .windowInsetsPadding(WindowInsets.navigationBars)
                    .imePadding(),
            )
        },
    ) { innerPadding ->
        ChatMessages(
            uiState = uiState,
            listState = listState,
            isTtsAvailable = isTtsAvailable,
            onSpeak = { text -> coroutineScope.launch { textToSpeech?.say(text) } },
            onToggleFavorite = { messageId -> viewModel.onAction(ChatAction.Ui.FavoriteToggled(messageId)) },
            onCopy = { viewModel.onAction(ChatAction.Ui.MessageCopied) },
            onRetryClick = { viewModel.onAction(ChatAction.Ui.RetryClicked) },
            modifier = Modifier.padding(innerPadding),
        )
    }
}

@Composable
private fun ChatTopBarActions(
    isFavoritesFilterActive: Boolean,
    onFavoritesClick: () -> Unit,
    onExportClick: () -> Unit,
    onImportClick: () -> Unit,
    onClearHistoryClick: () -> Unit,
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
}

@Composable
private fun ClearHistoryConfirmationDialog(
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
private fun ChatMessages(
    uiState: ChatUiModel,
    listState: LazyListState,
    isTtsAvailable: Boolean,
    onSpeak: (String) -> Unit,
    onToggleFavorite: (String) -> Unit,
    onCopy: () -> Unit,
    onRetryClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val isEmpty = uiState.messages.isEmpty() && !uiState.isLoading && !uiState.isErrorVisible
    Box(modifier = modifier.fillMaxSize()) {
        if (isEmpty) {
            Text(
                text = if (uiState.isFavoritesFilterActive) EMPTY_FAVORITES_HINT else EMPTY_HINT,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier
                    .align(Alignment.Center)
                    .padding(ChatDimens.spacingMd),
            )
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(ChatDimens.spacingMd),
                verticalArrangement = Arrangement.spacedBy(ChatDimens.spacingXs),
            ) {
                items(items = uiState.messages, key = { message -> message.id }) { message ->
                    MessageBubble(
                        message = message,
                        isTtsAvailable = isTtsAvailable,
                        onSpeak = onSpeak,
                        onToggleFavorite = onToggleFavorite,
                        onCopy = onCopy,
                    )
                }
                if (uiState.isLoading) {
                    item {
                        TypingIndicator(modifier = Modifier.fillMaxWidth())
                    }
                }
                if (uiState.isErrorVisible) {
                    item {
                        Column(modifier = Modifier.fillMaxWidth()) {
                            Text(
                                text = ERROR_MESSAGE,
                                color = MaterialTheme.colorScheme.error,
                                modifier = Modifier.fillMaxWidth(),
                            )
                            TextButton(onClick = onRetryClick) {
                                Icon(
                                    imageVector = Icons.Filled.Refresh,
                                    contentDescription = null,
                                )
                                Text(text = RETRY_BUTTON_TEXT)
                            }
                        }
                    }
                }
            }
        }
    }
}
