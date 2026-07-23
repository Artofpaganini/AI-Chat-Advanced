package com.jarvis.chat.feature.voice

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import com.jarvis.chat.feature.voice.model.SpeechRecognitionStateModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

@Composable
actual fun rememberSpeechRecognitionController(
    onTranscript: (String) -> Unit,
): SpeechRecognitionController = remember {
    object : SpeechRecognitionController {

        private val mutableState =
            MutableStateFlow<SpeechRecognitionStateModel>(SpeechRecognitionStateModel.Unavailable)

        override val state: StateFlow<SpeechRecognitionStateModel> = mutableState.asStateFlow()

        override fun toggle() = Unit

        override fun start() = Unit

        override fun stop() = Unit
    }
}
