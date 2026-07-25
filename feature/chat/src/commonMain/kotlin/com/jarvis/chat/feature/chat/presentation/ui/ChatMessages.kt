package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import com.jarvis.chat.feature.chat.presentation.model.ChatUiModel

private const val EMPTY_FAVORITES_HINT = "No favorites yet. Tap the star icon on an answer to save it."
private const val RETRY_BUTTON_TEXT = "Retry"

@Composable
internal fun ChatMessages(
    uiState: ChatUiModel,
    listState: LazyListState,
    isTtsAvailable: Boolean,
    onSpeak: (String) -> Unit,
    onToggleFavorite: (String) -> Unit,
    onCopy: () -> Unit,
    onDeleteRequest: (String) -> Unit,
    onRetryClick: () -> Unit,
    onSuggestionClick: (String) -> Unit,
    onScrollToBottomClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier.fillMaxSize()) {
        if (uiState.isEmptyState) {
            ChatEmptyState(onSuggestionClick = onSuggestionClick)
        } else if (uiState.isFavoritesEmptyState) {
            Text(
                text = EMPTY_FAVORITES_HINT,
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
                        onDeleteRequest = onDeleteRequest,
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
                                text = uiState.errorMessage.orEmpty(),
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

            ScrollToBottomFab(
                listState = listState,
                onClick = onScrollToBottomClick,
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(ChatDimens.spacingMd),
            )
        }
    }
}
