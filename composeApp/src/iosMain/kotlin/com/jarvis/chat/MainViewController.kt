package com.jarvis.chat

import androidx.compose.ui.window.ComposeUIViewController
import com.jarvis.chat.di.initKoin
import platform.Foundation.NSDocumentDirectory
import platform.Foundation.NSSearchPathForDirectoriesInDomains
import platform.Foundation.NSUserDomainMask
import platform.UIKit.UIViewController

@Suppress("unused")
fun mainViewController(): UIViewController {
    initKoin(
        appConfig = AppConfig(
            deepSeekApiKey = "",
            filesDirectoryPath = resolveDocumentsDirectoryPath(),
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
