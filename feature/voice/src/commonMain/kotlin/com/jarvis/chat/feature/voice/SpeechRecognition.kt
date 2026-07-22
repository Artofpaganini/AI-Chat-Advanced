package com.jarvis.chat.feature.voice

import androidx.compose.runtime.Composable

@Composable
expect fun rememberSpeechRecognitionController(
    onTranscript: (String) -> Unit,
): SpeechRecognitionController
