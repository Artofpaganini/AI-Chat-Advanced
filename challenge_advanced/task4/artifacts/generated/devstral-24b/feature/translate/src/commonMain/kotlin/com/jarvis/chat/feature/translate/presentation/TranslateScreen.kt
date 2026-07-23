package com.jarvis.chat.feature.translate.presentation

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.tooling.preview.Preview
import com.jarvis.chat.core.viewmodel.UdfViewModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

@Composable
internal fun TranslateScreen(viewModel: UdfViewModel<TranslateAction, TranslateUiModel>) {
    val uiState = viewModel.uiState.collectAsState().value
    val context = LocalContext.current

    Scaffold(
        topBar = { TopAppBar(title = { Text("Translate") }) }
    ) { padding ->
        Column(modifier = Modifier.padding(padding)) {
            OutlinedTextField(
                value = uiState.sourceText,
                onValueChange = { viewModel.onAction(TranslateAction.Ui(TranslateAction.UiAction.OnTranslate(it, TargetLanguage.ENGLISH))) },
                label = { Text("Source Text") }
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = uiState.translatedText,
                onValueChange = {},
                label = { Text("Translated Text") },
                readOnly = true
            )
            if (uiState.isLoading) {
                CircularProgressIndicator()
            }
            if (uiState.errorMessage != null) {
                Text(text = uiState.errorMessage, color = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@Preview
@Composable
private fun TranslateScreenPreview() {
    // Preview implementation here
}
