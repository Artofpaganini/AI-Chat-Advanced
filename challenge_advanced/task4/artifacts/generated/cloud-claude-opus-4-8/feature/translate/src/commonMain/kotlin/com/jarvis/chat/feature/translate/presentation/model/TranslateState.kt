package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.feature.translate.domain.model.TargetLanguage

internal data class TranslateState(
    val sourceText: String = "",
    val translatedText: String = "",
    val targetLanguage: TargetLanguage = TargetLanguage.ENGLISH,
    val isLoading: Boolean = false,
    val hasError: Boolean = false,
)
