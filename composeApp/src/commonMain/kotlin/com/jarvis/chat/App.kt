package com.jarvis.chat

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.Composable
import com.jarvis.chat.feature.chat.presentation.ChatScreen
import com.jarvis.chat.feature.chat.presentation.GatewayAuditBottomSheet
import com.jarvis.chat.feature.chat.presentation.SessionsBottomSheet
import com.jarvis.chat.feature.chat.presentation.rememberOpenGatewayAuditAction
import com.jarvis.chat.feature.chat.presentation.rememberOpenSessionsAction
import com.jarvis.chat.feature.settings.presentation.SettingsBottomSheet
import com.jarvis.chat.feature.settings.presentation.model.ThemeModeUiModel
import com.jarvis.chat.feature.settings.presentation.rememberOpenSettingsAction
import com.jarvis.chat.feature.settings.presentation.rememberSelectedThemeMode
import com.jarvis.chat.ui.theme.JarvisTheme

@Composable
fun App() {
    val selectedThemeMode = rememberSelectedThemeMode()
    val onSettingsClick = rememberOpenSettingsAction()
    val onSessionsClick = rememberOpenSessionsAction()
    val onGatewayAuditClick = rememberOpenGatewayAuditAction()
    val isDarkTheme = when (selectedThemeMode) {
        ThemeModeUiModel.SYSTEM -> isSystemInDarkTheme()
        ThemeModeUiModel.LIGHT -> false
        ThemeModeUiModel.DARK -> true
    }

    JarvisTheme(darkTheme = isDarkTheme) {
        ChatScreen(
            onSettingsClick = onSettingsClick,
            onSessionsClick = onSessionsClick,
            onGatewayAuditClick = onGatewayAuditClick,
        )
        SettingsBottomSheet()
        SessionsBottomSheet()
        GatewayAuditBottomSheet()
    }
}
