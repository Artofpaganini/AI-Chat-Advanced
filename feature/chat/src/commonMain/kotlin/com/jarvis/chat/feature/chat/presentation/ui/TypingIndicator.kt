package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier

private const val TYPING_INDICATOR_TEXT = "Jarvis is typing..."

@Composable
internal fun TypingIndicator(modifier: Modifier = Modifier) {
    Box(
        modifier = modifier.fillMaxWidth(),
        contentAlignment = Alignment.CenterStart,
    ) {
        Surface(
            color = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurfaceVariant,
            shape = MaterialTheme.shapes.large,
            tonalElevation = ChatDimens.elevationLow,
            modifier = Modifier.widthIn(max = ChatDimens.messageBubbleMaxWidth),
        ) {
            Row(
                modifier = Modifier.padding(ChatDimens.spacingSm),
                horizontalArrangement = Arrangement.spacedBy(ChatDimens.spacingXs),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                CircularProgressIndicator(modifier = Modifier.size(ChatDimens.typingIndicatorSize))
                Text(
                    text = TYPING_INDICATOR_TEXT,
                    style = MaterialTheme.typography.bodyLarge,
                )
            }
        }
    }
}
