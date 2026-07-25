package com.jarvis.chat

import androidx.compose.runtime.Composable
import com.jarvis.chat.feature.chat.presentation.ChatScreen
import com.jarvis.chat.ui.theme.JarvisTheme

@Composable
fun App() {
    JarvisTheme {
        ChatScreen()
    }
}
