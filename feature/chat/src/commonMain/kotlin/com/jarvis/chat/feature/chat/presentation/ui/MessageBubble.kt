package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.outlined.StarBorder
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.jarvis.chat.feature.chat.presentation.model.ChatMessageUiModel

private const val SPEAK_CONTENT_DESCRIPTION = "Speak message aloud"
private const val FAVORITE_ACTIVE_CONTENT_DESCRIPTION = "Remove from favorites"
private const val FAVORITE_INACTIVE_CONTENT_DESCRIPTION = "Add to favorites"

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
            tonalElevation = ChatDimens.elevationLow,
            modifier = Modifier.widthIn(max = ChatDimens.messageBubbleMaxWidth),
        ) {
            Column(
                modifier = Modifier.padding(ChatDimens.spacingSm),
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
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.VolumeUp,
                    contentDescription = SPEAK_CONTENT_DESCRIPTION,
                )
            }
        }
        if (message.canFavorite) {
            IconButton(onClick = { onToggleFavorite(message.id) }) {
                Icon(
                    imageVector = if (message.isFavorite) Icons.Filled.Star else Icons.Outlined.StarBorder,
                    contentDescription = if (message.isFavorite) {
                        FAVORITE_ACTIVE_CONTENT_DESCRIPTION
                    } else {
                        FAVORITE_INACTIVE_CONTENT_DESCRIPTION
                    },
                )
            }
        }
    }
}
