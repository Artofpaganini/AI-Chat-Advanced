package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import kotlin.js.ExperimentalWasmJsInterop

private const val JSON_FILE_ACCEPT = ".json,application/json"

@OptIn(ExperimentalWasmJsInterop::class)
@JsFun(
    """
    (accept, onText, onError) => {
        try {
            const input = document.createElement('input')
            input.type = 'file'
            input.accept = accept
            input.onchange = () => {
                const file = input.files && input.files[0]
                if (!file) {
                    return
                }
                const reader = new FileReader()
                reader.onload = () => onText(String(reader.result))
                reader.onerror = () => onError()
                reader.readAsText(file)
            }
            input.click()
        } catch (error) {
            onError()
        }
    }
    """,
)
private external fun openJsonFilePicker(accept: String, onText: (String) -> Unit, onError: () -> Unit)

@Composable
internal actual fun rememberJsonFilePicker(
    onFilePicked: (String) -> Unit,
    onFailure: () -> Unit,
): () -> Unit {
    val latestOnFilePicked by rememberUpdatedState(onFilePicked)
    val latestOnFailure by rememberUpdatedState(onFailure)
    return remember {
        { openJsonFilePicker(JSON_FILE_ACCEPT, latestOnFilePicked, latestOnFailure) }
    }
}
