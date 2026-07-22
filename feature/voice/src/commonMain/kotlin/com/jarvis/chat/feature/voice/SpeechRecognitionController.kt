package com.jarvis.chat.feature.voice

import com.jarvis.chat.feature.voice.model.SpeechRecognitionStateModel
import kotlinx.coroutines.flow.StateFlow

interface SpeechRecognitionController {

    val state: StateFlow<SpeechRecognitionStateModel>

    fun toggle()

    fun start()

    fun stop()
}
