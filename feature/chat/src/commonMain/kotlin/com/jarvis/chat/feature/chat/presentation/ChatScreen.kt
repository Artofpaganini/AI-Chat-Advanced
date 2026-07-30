package com.jarvis.chat.feature.chat.presentation

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import com.jarvis.chat.feature.chat.presentation.model.ChatAction
import com.jarvis.chat.feature.chat.presentation.model.ChatEvent
import com.jarvis.chat.feature.chat.presentation.ui.ChatMessages
import com.jarvis.chat.feature.chat.presentation.ui.ChatTopBarActions
import com.jarvis.chat.feature.chat.presentation.ui.ClearHistoryConfirmationDialog
import com.jarvis.chat.feature.chat.presentation.ui.DeleteMessageConfirmationDialog
import com.jarvis.chat.feature.chat.presentation.ui.MessageInputBar
import com.jarvis.chat.feature.chat.presentation.ui.buildSpeechText
import com.jarvis.chat.feature.chat.presentation.ui.isScrolledToBottom
import com.jarvis.chat.feature.chat.presentation.ui.rememberJsonFilePicker
import com.jarvis.chat.feature.voice.model.SpeechRecognitionStateModel
import com.jarvis.chat.feature.voice.rememberSpeechRecognitionController
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import nl.marc_apps.tts.TextToSpeechInstance
import nl.marc_apps.tts.rememberTextToSpeechOrNull
import org.koin.compose.viewmodel.koinViewModel

private const val TITLE = "Jarvis"
private const val IMPORT_READ_FAILED_MESSAGE = "Failed to read file. Please try again."
private const val SPEECH_PLAYBACK_FAILED_MESSAGE = "Speech playback failed."
private const val SCROLL_TO_BOTTOM_TARGET_INDEX = Int.MAX_VALUE

@Composable
fun ChatScreen(onSettingsClick: () -> Unit, onSessionsClick: () -> Unit, modifier: Modifier = Modifier) {
    ChatContent(onSettingsClick = onSettingsClick, onSessionsClick = onSessionsClick, modifier = modifier)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun ChatContent(
    onSettingsClick: () -> Unit,
    onSessionsClick: () -> Unit,
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
    val importJsonFile = rememberJsonFilePicker(
        onFilePicked = { json -> viewModel.onAction(ChatAction.Ui.ImportRequested(json)) },
        onFailure = {
            coroutineScope.launch { snackbarHostState.showSnackbar(IMPORT_READ_FAILED_MESSAGE) }
        },
    )
    val scrollToBottom: suspend () -> Unit = {
        listState.animateScrollToItem(index = SCROLL_TO_BOTTOM_TARGET_INDEX)
    }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                ChatEvent.ScrollToBottom -> scrollToBottom()
                is ChatEvent.ShowMessage -> snackbarHostState.showSnackbar(event.text)
            }
        }
    }

    val lastMessageTextLength = uiState.messages.lastOrNull()?.text?.length ?: 0
    LaunchedEffect(uiState.messages.size, lastMessageTextLength) {
        if (listState.isScrolledToBottom()) {
            scrollToBottom()
        }
    }

    val imeBottomPxState = rememberUpdatedState(WindowInsets.ime.getBottom(LocalDensity.current))
    LaunchedEffect(listState) {
        var wasAtBottomBeforeImeOpened = false
        var previousImeBottomPx = imeBottomPxState.value
        snapshotFlow { imeBottomPxState.value }.collect { imeBottomPx ->
            val imeStartedOpening = previousImeBottomPx <= 0 && imeBottomPx > 0
            if (imeStartedOpening) {
                wasAtBottomBeforeImeOpened = listState.isScrolledToBottom()
            }
            if (imeBottomPx > 0 && wasAtBottomBeforeImeOpened) {
                listState.scrollToItem(index = SCROLL_TO_BOTTOM_TARGET_INDEX)
            }
            if (imeBottomPx <= 0) {
                wasAtBottomBeforeImeOpened = false
            }
            previousImeBottomPx = imeBottomPx
        }
    }

    val speakingMessage = uiState.messages.find { message -> message.isSpeaking }
    LaunchedEffect(speakingMessage?.id, textToSpeech) {
        val message = speakingMessage ?: return@LaunchedEffect
        val ttsEngine = textToSpeech ?: return@LaunchedEffect
        ttsEngine.speakOrStop(buildSpeechText(message.text))
            .onFailure { snackbarHostState.showSnackbar(SPEECH_PLAYBACK_FAILED_MESSAGE) }
        viewModel.onAction(ChatAction.Ui.SpeechFinished(message.id))
    }

    if (uiState.showClearConfirmation) {
        ClearHistoryConfirmationDialog(
            onConfirm = { viewModel.onAction(ChatAction.Ui.ClearHistoryConfirmed) },
            onDismiss = { viewModel.onAction(ChatAction.Ui.ClearHistoryCancelled) },
        )
    }

    if (uiState.isDeleteMessageConfirmationVisible) {
        DeleteMessageConfirmationDialog(
            onConfirm = { viewModel.onAction(ChatAction.Ui.DeleteMessageConfirmed) },
            onDismiss = { viewModel.onAction(ChatAction.Ui.DeleteMessageCancelled) },
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
                        onSessionsClick = onSessionsClick,
                        onFavoritesClick = { viewModel.onAction(ChatAction.Ui.FavoritesFilterToggled) },
                        onExportClick = { viewModel.onAction(ChatAction.Ui.ExportClicked) },
                        onImportClick = importJsonFile,
                        onClearHistoryClick = { viewModel.onAction(ChatAction.Ui.ClearHistoryClicked) },
                        onSettingsClick = onSettingsClick,
                    )
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            MessageInputBar(
                inputText = uiState.inputText,
                isSendEnabled = uiState.isSendEnabled,
                isGenerating = uiState.isGenerating,
                isListening = isListening,
                onInputChange = { text -> viewModel.onAction(ChatAction.Ui.InputChanged(text)) },
                onSendClick = { viewModel.onAction(ChatAction.Ui.SendClicked) },
                onStopClick = { viewModel.onAction(ChatAction.Ui.StopClicked) },
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
            onSpeakToggle = { messageId -> viewModel.onAction(ChatAction.Ui.SpeakToggled(messageId)) },
            onToggleFavorite = { messageId -> viewModel.onAction(ChatAction.Ui.FavoriteToggled(messageId)) },
            onCopy = { viewModel.onAction(ChatAction.Ui.MessageCopied) },
            onDeleteRequest = { messageId -> viewModel.onAction(ChatAction.Ui.DeleteMessageClicked(messageId)) },
            onRetryClick = { viewModel.onAction(ChatAction.Ui.RetryClicked) },
            onSuggestionClick = { suggestion -> viewModel.onAction(ChatAction.Ui.SuggestionClicked(suggestion)) },
            onScrollToBottomClick = { coroutineScope.launch { scrollToBottom() } },
            modifier = Modifier.padding(innerPadding),
        )
    }
}

@Suppress("TooGenericExceptionCaught")
private suspend fun TextToSpeechInstance.speakOrStop(text: String): Result<Unit> {
    val result = try {
        say(text = text, clearQueue = true)
        Result.success(Unit)
    } catch (cancellation: CancellationException) {
        throw cancellation
    } catch (throwable: Throwable) {
        Result.failure(throwable)
    } finally {
        stop()
    }
    return result
}
