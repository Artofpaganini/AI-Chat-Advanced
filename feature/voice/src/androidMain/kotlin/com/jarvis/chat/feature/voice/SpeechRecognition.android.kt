package com.jarvis.chat.feature.voice

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.platform.LocalContext

@Composable
actual fun rememberSpeechRecognitionController(
    onTranscript: (String) -> Unit,
): SpeechRecognitionController {
    val context = LocalContext.current
    val latestOnTranscript by rememberUpdatedState(onTranscript)
    val controller = remember(context) {
        AndroidSpeechRecognitionController(
            context = context.applicationContext,
            onTranscript = { text -> latestOnTranscript(text) },
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { isGranted -> controller.onPermissionResult(isGranted) }

    SideEffect {
        controller.attachPermissionRequester {
            permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    DisposableEffect(controller) {
        onDispose { controller.dispose() }
    }

    return controller
}
