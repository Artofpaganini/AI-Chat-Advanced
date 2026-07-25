package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.platform.ClipEntry

@OptIn(ExperimentalComposeUiApi::class)
internal actual fun createPlainTextClipEntry(text: String): ClipEntry = ClipEntry.withPlainText(text)
