package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember

@Composable
internal actual fun rememberJsonFilePicker(
    onFilePicked: (String) -> Unit,
    onFailure: () -> Unit,
): () -> Unit = remember { {} }
