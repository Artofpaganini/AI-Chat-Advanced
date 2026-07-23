package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal data class TranslateUiModel(
    val sourceText: String,
    val targetLanguage: TargetLanguage,
    val translationModel: TranslationModel?,
    val errorMessage: String?,
)
