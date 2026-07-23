package com.jarvis.chat.feature.translate.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction

@Composable
internal fun TranslateScreen(viewModel: TranslateViewModel) {
    var inputText by remember { mutableStateOf("") }
    var targetLanguage by remember { mutableStateOf("ru") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        OutlinedTextField(
            value = inputText,
            onValueChange = { inputText = it },
            label = { Text("Enter text to translate") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = targetLanguage,
            onValueChange = { targetLanguage = it },
            label = { Text("Target language") },
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Text)
        )

        Button(
            onClick = {
                viewModel.onAction(TranslateAction.Translate(inputText, targetLanguage))
            }
        ) {
            Text("Translate")
        }

        // TODO: Add error handling and loading indicator
    }
}
