package com.jarvis.chat

import androidx.compose.ui.window.ComposeUIViewController
import com.jarvis.chat.di.initKoin
import platform.UIKit.UIViewController

@Suppress("unused")
fun mainViewController(): UIViewController {
    initKoin(appConfig = AppConfig(deepSeekApiKey = ""))
    return ComposeUIViewController { App() }
}
