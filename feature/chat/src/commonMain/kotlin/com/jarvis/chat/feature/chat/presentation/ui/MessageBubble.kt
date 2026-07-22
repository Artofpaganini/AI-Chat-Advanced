package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.jarvis.chat.feature.chat.presentation.model.ChatMessageUiModel

private val bubbleMaxWidth = 320.dp
private val bubbleContentPadding = 12.dp
private val bubbleElevation = 1.dp
private const val SPEAKER_LABEL = "🔊"
private const val FAVORITE_ACTIVE_LABEL = "★"
private const val FAVORITE_INACTIVE_LABEL = "☆"

@Composable
internal fun MessageBubble(
    message: ChatMessageUiModel,
    isTtsAvailable: Boolean,
    onSpeak: (String) -> Unit,
    onToggleFavorite: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val isFromUser = message.isFromUser
    val bubbleColor = if (isFromUser) {
        MaterialTheme.colorScheme.primary
    } else {
        MaterialTheme.colorScheme.surfaceVariant
    }
    val contentColor = if (isFromUser) {
        MaterialTheme.colorScheme.onPrimary
    } else {
        MaterialTheme.colorScheme.onSurfaceVariant
    }
    Box(
        modifier = modifier.fillMaxWidth(),
        contentAlignment = if (isFromUser) Alignment.CenterEnd else Alignment.CenterStart,
    ) {
        Surface(
            color = bubbleColor,
            contentColor = contentColor,
            shape = MaterialTheme.shapes.large,
            tonalElevation = bubbleElevation,
            modifier = Modifier.widthIn(max = bubbleMaxWidth),
        ) {
            Column(
                modifier = Modifier.padding(bubbleContentPadding),
                horizontalAlignment = Alignment.Start,
            ) {
                Text(
                    text = message.text,
                    style = MaterialTheme.typography.bodyLarge,
                )
                MessageActions(
                    message = message,
                    isTtsAvailable = isTtsAvailable,
                    onSpeak = onSpeak,
                    onToggleFavorite = onToggleFavorite,
                )
            }
        }
    }
}

@Composable
private fun MessageActions(
    message: ChatMessageUiModel,
    isTtsAvailable: Boolean,
    onSpeak: (String) -> Unit,
    onToggleFavorite: (String) -> Unit,
) {
    if (!message.isSpeakable && !message.canFavorite) {
        return
    }
    Row(horizontalArrangement = Arrangement.Start) {
        if (message.isSpeakable) {
            IconButton(
                onClick = { onSpeak(message.text) },
                enabled = isTtsAvailable,
            ) {
                Text(text = SPEAKER_LABEL)
            }
        }
        if (message.canFavorite) {
            IconButton(onClick = { onToggleFavorite(message.id) }) {
                Text(text = if (message.isFavorite) FAVORITE_ACTIVE_LABEL else FAVORITE_INACTIVE_LABEL)
            }
        }
    }
}
