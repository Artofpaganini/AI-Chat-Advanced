package com.jarvis.chat.feature.settings.presentation

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.jarvis.chat.feature.settings.presentation.model.SettingsAction
import com.jarvis.chat.feature.settings.presentation.model.ThemeModeUiModel
import com.jarvis.chat.feature.settings.presentation.ui.SettingsDimens
import org.koin.compose.viewmodel.koinViewModel

private const val SETTINGS_TITLE = "Theme"
private const val THEME_LABEL_SYSTEM = "System default"
private const val THEME_LABEL_LIGHT = "Light"
private const val THEME_LABEL_DARK = "Dark"

@Composable
fun rememberSelectedThemeMode(): ThemeModeUiModel {
    val viewModel: SettingsViewModel = koinViewModel()
    val uiState by viewModel.uiState.collectAsState()
    return uiState.selectedThemeMode
}

@Composable
fun rememberOpenSettingsAction(): () -> Unit {
    val viewModel: SettingsViewModel = koinViewModel()
    return remember(viewModel) { { viewModel.onAction(SettingsAction.Ui.OpenClicked) } }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsBottomSheet() {
    val viewModel: SettingsViewModel = koinViewModel()
    val uiState by viewModel.uiState.collectAsState()

    if (uiState.isSheetVisible) {
        ModalBottomSheet(onDismissRequest = { viewModel.onAction(SettingsAction.Ui.DismissRequested) }) {
            ThemeModeOptions(
                selectedThemeMode = uiState.selectedThemeMode,
                onThemeModeSelected = { themeMode -> viewModel.onAction(SettingsAction.Ui.ThemeModeSelected(themeMode)) },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(SettingsDimens.spacingMd)
                    .navigationBarsPadding(),
            )
        }
    }
}

@Composable
private fun ThemeModeOptions(
    selectedThemeMode: ThemeModeUiModel,
    onThemeModeSelected: (ThemeModeUiModel) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier) {
        Text(text = SETTINGS_TITLE, style = MaterialTheme.typography.titleMedium)
        ThemeModeUiModel.entries.forEach { themeMode ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onThemeModeSelected(themeMode) }
                    .padding(vertical = SettingsDimens.spacingXs),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RadioButton(
                    selected = themeMode == selectedThemeMode,
                    onClick = { onThemeModeSelected(themeMode) },
                )
                Text(text = themeMode.toLabel())
            }
        }
    }
}

private fun ThemeModeUiModel.toLabel(): String =
    when (this) {
        ThemeModeUiModel.SYSTEM -> THEME_LABEL_SYSTEM
        ThemeModeUiModel.LIGHT -> THEME_LABEL_LIGHT
        ThemeModeUiModel.DARK -> THEME_LABEL_DARK
    }
