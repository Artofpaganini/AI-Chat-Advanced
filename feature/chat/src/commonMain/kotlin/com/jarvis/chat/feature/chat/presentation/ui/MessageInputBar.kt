package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

private val barPadding = 12.dp
private val elementSpacing = 8.dp
private val barElevation = 3.dp
private const val INPUT_MAX_LINES = 5
private const val INPUT_PLACEHOLDER = "Message Jarvis…"
private const val SEND_LABEL = "Send"
private const val MIC_IDLE_LABEL = "🎤"
private const val MIC_ACTIVE_LABEL = "⏹"

@Composable
internal fun MessageInputBar(
    inputText: String,
    isSendEnabled: Boolean,
    isListening: Boolean,
    onInputChange: (String) -> Unit,
    onSendClick: () -> Unit,
    onMicClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        tonalElevation = barElevation,
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(barPadding),
            verticalAlignment = Alignment.Bottom,
        ) {
            FilledIconButton(
                onClick = onMicClick,
                colors = if (isListening) {
                    IconButtonDefaults.filledIconButtonColors()
                } else {
                    IconButtonDefaults.filledTonalIconButtonColors()
                },
            ) {
                Text(text = if (isListening) MIC_ACTIVE_LABEL else MIC_IDLE_LABEL)
            }
            Spacer(modifier = Modifier.width(elementSpacing))
            OutlinedTextField(
                value = inputText,
                onValueChange = onInputChange,
                modifier = Modifier.weight(1f),
                placeholder = { Text(text = INPUT_PLACEHOLDER) },
                maxLines = INPUT_MAX_LINES,
            )
            Spacer(modifier = Modifier.width(elementSpacing))
            Button(
                onClick = onSendClick,
                enabled = isSendEnabled,
            ) {
                Text(text = SEND_LABEL)
            }
        }
    }
}
