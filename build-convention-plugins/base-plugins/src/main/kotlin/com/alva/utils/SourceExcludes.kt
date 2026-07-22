@file:Suppress("ktlint")

package com.alva.utils

/**
 * Общий список glob-паттернов путей, исключённых из статического анализа
 * (detekt + ktlint). Единый источник правды, чтобы excludes не расходились
 * между двумя плагинами.
 */
internal val sourceExcludeGlobs: List<String> = listOf(
    "**/build/**",
    "**/.gradle/**",
    "**/iosX64Main/**",
    "**/showcaseApp/**",
    "gradle/build-logic",
)
