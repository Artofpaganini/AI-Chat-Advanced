package com.jarvis.chat.feature.voice.model

sealed interface SpeechRecognitionStateModel {

    data object Idle : SpeechRecognitionStateModel

    data object Listening : SpeechRecognitionStateModel

    data object PermissionDenied : SpeechRecognitionStateModel

    data object Unavailable : SpeechRecognitionStateModel

    data class Failed(val message: String) : SpeechRecognitionStateModel
}
