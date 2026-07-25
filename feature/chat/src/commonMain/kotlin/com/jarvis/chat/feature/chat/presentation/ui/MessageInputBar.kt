package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier

private const val INPUT_MAX_LINES = 5
private const val INPUT_PLACEHOLDER = "Message Jarvis…"
private const val SEND_CONTENT_DESCRIPTION = "Send message"
private const val STOP_CONTENT_DESCRIPTION = "Stop generating response"
private const val MIC_IDLE_CONTENT_DESCRIPTION = "Start voice input"
private const val MIC_ACTIVE_CONTENT_DESCRIPTION = "Stop voice input"

@Composable
internal fun MessageInputBar(
    inputText: String,
    isSendEnabled: Boolean,
    isGenerating: Boolean,
    isListening: Boolean,
    onInputChange: (String) -> Unit,
    onSendClick: () -> Unit,
    onStopClick: () -> Unit,
    onMicClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        tonalElevation = ChatDimens.elevationHigh,
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(ChatDimens.spacingSm),
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
                Icon(
                    imageVector = if (isListening) Icons.Filled.Stop else Icons.Filled.Mic,
                    contentDescription = if (isListening) {
                        MIC_ACTIVE_CONTENT_DESCRIPTION
                    } else {
                        MIC_IDLE_CONTENT_DESCRIPTION
                    },
                )
            }
            Spacer(modifier = Modifier.width(ChatDimens.spacingXs))
            OutlinedTextField(
                value = inputText,
                onValueChange = onInputChange,
                modifier = Modifier.weight(1f),
                placeholder = { Text(text = INPUT_PLACEHOLDER) },
                maxLines = INPUT_MAX_LINES,
            )
            Spacer(modifier = Modifier.width(ChatDimens.spacingXs))
            Button(
                onClick = if (isGenerating) onStopClick else onSendClick,
                enabled = if (isGenerating) true else isSendEnabled,
            ) {
                Icon(
                    imageVector = if (isGenerating) Icons.Filled.Stop else Icons.AutoMirrored.Filled.Send,
                    contentDescription = if (isGenerating) STOP_CONTENT_DESCRIPTION else SEND_CONTENT_DESCRIPTION,
                )
            }
        }
    }
}
