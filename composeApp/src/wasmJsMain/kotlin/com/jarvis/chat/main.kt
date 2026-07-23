package com.jarvis.chat

import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.window.ComposeViewport
import com.jarvis.chat.di.initKoin
import kotlinx.browser.document
import kotlinx.browser.window

@OptIn(ExperimentalComposeUiApi::class)
fun main() {
    initKoin(
        appConfig = AppConfig(
            deepSeekApiKey = JarvisWebConfig.DEEPSEEK_API_KEY,
            deepSeekBaseUrl = window.location.origin + "/",
            filesDirectoryPath = "",
        ),
    )
    ComposeViewport(document.body!!) {
        App()
    }
}
