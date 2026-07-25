package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.runtime.Composable

@Composable
internal expect fun rememberJsonFilePicker(
    onFilePicked: (String) -> Unit,
    onFailure: () -> Unit,
): () -> Unit
