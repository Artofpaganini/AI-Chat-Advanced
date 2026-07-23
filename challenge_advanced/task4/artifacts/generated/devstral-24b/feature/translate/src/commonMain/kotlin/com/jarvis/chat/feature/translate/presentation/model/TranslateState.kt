package com.jarvis.chat.feature.translate.presentation.model

internal data class TranslateState(
    val sourceText: String = "",
    val targetLanguage: TargetLanguage? = null,
    val translatedText: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)
