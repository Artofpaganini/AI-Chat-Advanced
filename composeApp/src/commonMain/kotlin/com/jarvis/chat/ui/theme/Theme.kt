package com.jarvis.chat.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val JarvisLightColorScheme = lightColorScheme(
    primary = JarvisCyanLight,
    onPrimary = JarvisOnCyanLight,
    primaryContainer = JarvisCyanContainerLight,
    onPrimaryContainer = JarvisOnCyanContainerLight,
    secondary = JarvisBlueLight,
    onSecondary = JarvisOnBlueLight,
    secondaryContainer = JarvisBlueContainerLight,
    onSecondaryContainer = JarvisOnBlueContainerLight,
    tertiary = JarvisVioletLight,
    onTertiary = JarvisOnVioletLight,
    tertiaryContainer = JarvisVioletContainerLight,
    onTertiaryContainer = JarvisOnVioletContainerLight,
    error = JarvisErrorLight,
    onError = JarvisOnErrorLight,
    errorContainer = JarvisErrorContainerLight,
    onErrorContainer = JarvisOnErrorContainerLight,
    background = JarvisBackgroundLight,
    onBackground = JarvisOnBackgroundLight,
    surface = JarvisSurfaceLight,
    onSurface = JarvisOnSurfaceLight,
    surfaceVariant = JarvisSurfaceVariantLight,
    onSurfaceVariant = JarvisOnSurfaceVariantLight,
    outline = JarvisOutlineLight,
)

private val JarvisDarkColorScheme = darkColorScheme(
    primary = JarvisCyanDark,
    onPrimary = JarvisOnCyanDark,
    primaryContainer = JarvisCyanContainerDark,
    onPrimaryContainer = JarvisOnCyanContainerDark,
    secondary = JarvisBlueDark,
    onSecondary = JarvisOnBlueDark,
    secondaryContainer = JarvisBlueContainerDark,
    onSecondaryContainer = JarvisOnBlueContainerDark,
    tertiary = JarvisVioletDark,
    onTertiary = JarvisOnVioletDark,
    tertiaryContainer = JarvisVioletContainerDark,
    onTertiaryContainer = JarvisOnVioletContainerDark,
    error = JarvisErrorDark,
    onError = JarvisOnErrorDark,
    errorContainer = JarvisErrorContainerDark,
    onErrorContainer = JarvisOnErrorContainerDark,
    background = JarvisBackgroundDark,
    onBackground = JarvisOnBackgroundDark,
    surface = JarvisSurfaceDark,
    onSurface = JarvisOnSurfaceDark,
    surfaceVariant = JarvisSurfaceVariantDark,
    onSurfaceVariant = JarvisOnSurfaceVariantDark,
    outline = JarvisOutlineDark,
)

@Composable
internal fun JarvisTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colorScheme = if (darkTheme) JarvisDarkColorScheme else JarvisLightColorScheme
    MaterialTheme(
        colorScheme = colorScheme,
        content = content,
    )
}
