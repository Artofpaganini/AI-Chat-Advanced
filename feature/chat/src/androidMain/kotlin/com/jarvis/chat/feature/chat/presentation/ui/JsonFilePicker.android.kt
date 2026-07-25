package com.jarvis.chat.feature.chat.presentation.ui

import android.content.Context
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.platform.LocalContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val JSON_MIME_TYPE = "application/json"

@Composable
internal actual fun rememberJsonFilePicker(
    onFilePicked: (String) -> Unit,
    onFailure: () -> Unit,
): () -> Unit {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val latestOnFilePicked by rememberUpdatedState(onFilePicked)
    val latestOnFailure by rememberUpdatedState(onFailure)
    val launcher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri == null) {
            return@rememberLauncherForActivityResult
        }
        coroutineScope.launch {
            val text = readTextFromUri(context = context, uri = uri)
            if (text != null) {
                latestOnFilePicked(text)
            } else {
                latestOnFailure()
            }
        }
    }
    return remember {
        { launcher.launch(arrayOf(JSON_MIME_TYPE)) }
    }
}

private suspend fun readTextFromUri(context: Context, uri: Uri): String? =
    withContext(Dispatchers.IO) {
        runCatching {
            context.contentResolver.openInputStream(uri)?.bufferedReader()?.use { reader -> reader.readText() }
        }.getOrNull()
    }
