package com.jarvis.chat.feature.translate.presentation

import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import org.koin.androidx.compose.viewModel

@Composable
fun TranslateScreen() {
    val viewModel = viewModel<TranslateViewModel>()
}

@Preview
@Composable
fun PreviewTranslateScreen() {
    TranslateScreen()
}
