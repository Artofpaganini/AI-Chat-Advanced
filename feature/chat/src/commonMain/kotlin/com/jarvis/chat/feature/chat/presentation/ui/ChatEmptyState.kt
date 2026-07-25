package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign

private const val GREETING_TITLE = "Hi, I'm Jarvis"
private const val GREETING_SUBTITLE = "Ask me anything — from quick facts to code and creative ideas."

private val SUGGESTIONS = listOf(
    "Explain quantum computing simply",
    "Write a short poem about the ocean",
    "Help me debug a Kotlin coroutine",
    "Suggest a healthy weekly meal plan",
)

@Composable
internal fun ChatEmptyState(
    onSuggestionClick: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(ChatDimens.spacingMd),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Column(
            modifier = Modifier.widthIn(max = ChatDimens.emptyStateContentMaxWidth),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = GREETING_TITLE,
                style = MaterialTheme.typography.titleLarge,
                textAlign = TextAlign.Center,
            )
            Text(
                text = GREETING_SUBTITLE,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = ChatDimens.spacingXs, bottom = ChatDimens.spacingMd),
            )
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(ChatDimens.spacingXs),
            ) {
                SUGGESTIONS.forEach { suggestion ->
                    SuggestionCard(text = suggestion, onClick = { onSuggestionClick(suggestion) })
                }
            }
        }
    }
}

@Composable
private fun SuggestionCard(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        onClick = onClick,
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surfaceVariant,
        contentColor = MaterialTheme.colorScheme.onSurfaceVariant,
        tonalElevation = ChatDimens.elevationLow,
        modifier = modifier.fillMaxWidth(),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(ChatDimens.spacingSm),
        )
    }
}
