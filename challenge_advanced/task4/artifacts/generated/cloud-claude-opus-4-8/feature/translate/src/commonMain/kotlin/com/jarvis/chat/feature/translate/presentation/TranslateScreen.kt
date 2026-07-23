package com.jarvis.chat.feature.translate.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

private val ScreenPadding = 16.dp
private val ItemSpacing = 12.dp

@Composable
internal fun TranslateScreen(
    uiModel: TranslateUiModel,
    onAction: (TranslateAction) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxWidth().padding(ScreenPadding),
        verticalArrangement = Arrangement.spacedBy(ItemSpacing),
    ) {
        OutlinedTextField(
            value = uiModel.sourceText,
            onValueChange = { text -> onAction(TranslateAction.Ui.InputChanged(text)) },
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(ItemSpacing)) {
            uiModel.languages.forEach { language ->
                FilterChip(
                    selected = language == uiModel.selectedLanguage,
                    onClick = { onAction(TranslateAction.Ui.LanguageSelected(language)) },
                    label = { Text(text = language.title) },
                )
            }
        }
        Button(
            onClick = { onAction(TranslateAction.Ui.TranslateClicked) },
            enabled = uiModel.isTranslateEnabled,
        ) {
            Text(text = "Перевести")
        }
        if (uiModel.isLoading) {
            CircularProgressIndicator()
        }
        if (uiModel.isResultVisible) {
            Text(text = uiModel.translatedText, style = MaterialTheme.typography.bodyLarge)
        }
        if (uiModel.isErrorVisible) {
            Text(
                text = "Перевод не удался",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error,
            )
        }
    }
}
