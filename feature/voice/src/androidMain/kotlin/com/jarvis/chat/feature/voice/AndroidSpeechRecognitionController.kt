package com.jarvis.chat.feature.voice

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import com.jarvis.chat.feature.voice.model.SpeechRecognitionStateModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

internal class AndroidSpeechRecognitionController(
    private val context: Context,
    private val onTranscript: (String) -> Unit,
) : SpeechRecognitionController {

    private val mutableState =
        MutableStateFlow<SpeechRecognitionStateModel>(SpeechRecognitionStateModel.Idle)

    override val state: StateFlow<SpeechRecognitionStateModel> = mutableState.asStateFlow()

    private var speechRecognizer: SpeechRecognizer? = null
    private var permissionRequester: (() -> Unit)? = null

    fun attachPermissionRequester(requester: () -> Unit) {
        permissionRequester = requester
    }

    override fun toggle() {
        if (mutableState.value == SpeechRecognitionStateModel.Listening) {
            stop()
        } else {
            start()
        }
    }

    override fun start() {
        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            mutableState.update { SpeechRecognitionStateModel.Unavailable }
            return
        }
        if (!hasRecordPermission()) {
            permissionRequester?.invoke()
            return
        }
        beginListening()
    }

    override fun stop() {
        speechRecognizer?.stopListening()
        if (mutableState.value == SpeechRecognitionStateModel.Listening) {
            mutableState.update { SpeechRecognitionStateModel.Idle }
        }
    }

    fun onPermissionResult(isGranted: Boolean) {
        if (isGranted) {
            beginListening()
        } else {
            mutableState.update { SpeechRecognitionStateModel.PermissionDenied }
        }
    }

    fun dispose() {
        speechRecognizer?.destroy()
        speechRecognizer = null
        permissionRequester = null
    }

    private fun hasRecordPermission(): Boolean =
        context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED

    private fun beginListening() {
        speechRecognizer?.destroy()
        val recognizer = SpeechRecognizer.createSpeechRecognizer(context)
        recognizer.setRecognitionListener(createRecognitionListener())
        speechRecognizer = recognizer
        mutableState.update { SpeechRecognitionStateModel.Listening }
        recognizer.startListening(createRecognizerIntent())
    }

    private fun createRecognizerIntent(): Intent =
        Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
            )
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
        }

    private fun createRecognitionListener(): RecognitionListener = object : RecognitionListener {

        override fun onReadyForSpeech(params: Bundle?) = Unit

        override fun onBeginningOfSpeech() = Unit

        override fun onRmsChanged(rmsdB: Float) = Unit

        override fun onBufferReceived(buffer: ByteArray?) = Unit

        override fun onEndOfSpeech() = Unit

        override fun onError(error: Int) {
            mutableState.update { SpeechRecognitionStateModel.Failed(mapError(error)) }
        }

        override fun onResults(results: Bundle?) {
            val recognized = results
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull()
                .orEmpty()
            if (recognized.isNotBlank()) {
                onTranscript(recognized)
            }
            mutableState.update { SpeechRecognitionStateModel.Idle }
        }

        override fun onPartialResults(partialResults: Bundle?) {
            val partial = partialResults
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull()
                .orEmpty()
            if (partial.isNotBlank()) {
                onTranscript(partial)
            }
        }

        override fun onEvent(eventType: Int, params: Bundle?) = Unit
    }

    private fun mapError(error: Int): String = when (error) {
        SpeechRecognizer.ERROR_NETWORK -> ERROR_NETWORK
        SpeechRecognizer.ERROR_NO_MATCH -> ERROR_NO_MATCH
        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> ERROR_TIMEOUT
        else -> ERROR_GENERIC
    }

    private companion object {
        const val ERROR_NETWORK = "Network error during speech recognition"
        const val ERROR_NO_MATCH = "No speech was recognized"
        const val ERROR_TIMEOUT = "No speech input detected"
        const val ERROR_GENERIC = "Speech recognition failed"
    }
}
