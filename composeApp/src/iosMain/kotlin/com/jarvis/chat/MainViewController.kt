package com.jarvis.chat

import androidx.compose.ui.window.ComposeUIViewController
import com.jarvis.chat.di.initKoin
import com.jarvis.chat.feature.ai.di.DeepSeekDefaults
import platform.Foundation.NSDocumentDirectory
import platform.Foundation.NSSearchPathForDirectoriesInDomains
import platform.Foundation.NSUserDomainMask
import platform.UIKit.UIViewController

private const val DEEPSEEK_BASE_URL = "https://api.deepseek.com/"

@Suppress("unused")
fun mainViewController(): UIViewController {
    initKoin(
        appConfig = AppConfig(
            deepSeekApiKey = "",
            deepSeekBaseUrl = DEEPSEEK_BASE_URL,
            filesDirectoryPath = resolveDocumentsDirectoryPath(),
            gatewayBaseUrl = DeepSeekDefaults.GATEWAY_BASE_URL,
        ),
    )
    return ComposeUIViewController { App() }
}

private fun resolveDocumentsDirectoryPath(): String {
    val paths = NSSearchPathForDirectoriesInDomains(
        directory = NSDocumentDirectory,
        domainMask = NSUserDomainMask,
        expandTilde = true,
    )
    return paths.firstOrNull() as? String ?: ""
}
