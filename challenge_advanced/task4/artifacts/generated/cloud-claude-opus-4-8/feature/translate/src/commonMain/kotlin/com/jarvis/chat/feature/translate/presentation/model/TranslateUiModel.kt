package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.feature.translate.domain.model.TargetLanguage

internal data class TranslateUiModel(
    val sourceText: String,
    val translatedText: String,
    val languages: List<TargetLanguage>,
    val selectedLanguage: TargetLanguage,
    val isLoading: Boolean,
    val isTranslateEnabled: Boolean,
    val isErrorVisible: Boolean,
    val isResultVisible: Boolean,
)
