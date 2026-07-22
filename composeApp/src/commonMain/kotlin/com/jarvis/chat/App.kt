package com.jarvis.chat

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import com.jarvis.chat.feature.chat.presentation.ChatScreen

@Composable
fun App() {
    MaterialTheme {
        ChatScreen()
    }
}
