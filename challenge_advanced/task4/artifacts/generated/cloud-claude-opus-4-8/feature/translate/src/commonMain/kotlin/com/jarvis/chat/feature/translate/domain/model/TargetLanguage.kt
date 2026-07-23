package com.jarvis.chat.feature.translate.domain.model

internal enum class TargetLanguage(val code: String, val title: String) {
    ENGLISH("en", "English"),
    RUSSIAN("ru", "Русский"),
    SPANISH("es", "Español"),
    GERMAN("de", "Deutsch"),
}
