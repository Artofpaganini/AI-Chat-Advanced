package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.ui.platform.ClipEntry

internal actual fun createPlainTextClipEntry(text: String): ClipEntry = ClipEntry.withPlainText(text)
