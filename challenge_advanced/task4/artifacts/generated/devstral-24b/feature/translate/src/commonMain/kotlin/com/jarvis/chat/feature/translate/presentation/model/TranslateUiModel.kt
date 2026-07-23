package com.jarvis.chat.feature.translate.presentation.model

internal data class TranslateUiModel(
    val sourceText: String,
    val targetLanguage: TargetLanguage?,
    val translatedText: String,
    val isLoading: Boolean,
    val errorMessage: String?
)
