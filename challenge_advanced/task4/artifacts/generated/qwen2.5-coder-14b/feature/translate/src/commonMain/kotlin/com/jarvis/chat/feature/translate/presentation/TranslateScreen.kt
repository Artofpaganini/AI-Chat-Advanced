package com.jarvis.chat.feature.translate.presentation

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.jarvis.chat.core.viewmodel.collectAsStateWithLifecycle
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

@Composable
fun TranslateScreen(viewModel: TranslateViewModel) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        TextField(
            value = uiState.sourceText,
            onValueChange = { viewModel.onAction(TranslateAction.Ui.InputText(it)) },
            label = { Text("Enter text to translate") },
            modifier = Modifier.fillMaxWidth(),
        )

        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            TargetLanguage.values().forEach { language ->
                Button(onClick = { viewModel.onAction(TranslateAction.Ui.SelectLanguage(language)) }) {
                    Text(text = language.name)
                }
            }
        }

        Button(onClick = { viewModel.onAction(TranslateAction.Ui.Translate) }) {
            Text("Translate")
        }

        uiState.translationModel?.let {
            Text(text = "Translated: ${it.translatedText}")
        }

        uiState.errorMessage?.let {
            Text(text = it, color = MaterialTheme.colorScheme.error)
        }
    }
}
