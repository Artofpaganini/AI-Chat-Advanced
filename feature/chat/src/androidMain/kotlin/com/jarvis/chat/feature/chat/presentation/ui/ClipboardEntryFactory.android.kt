package com.jarvis.chat.feature.chat.presentation.ui

import android.content.ClipData
import androidx.compose.ui.platform.ClipEntry

private const val MESSAGE_CLIP_LABEL = "message"

internal actual fun createPlainTextClipEntry(text: String): ClipEntry =
    ClipEntry(ClipData.newPlainText(MESSAGE_CLIP_LABEL, text))
