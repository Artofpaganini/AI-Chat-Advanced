package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal data class TranslateState(
    val sourceText: String = "",
    val targetLanguage: TargetLanguage = TargetLanguage.ENGLISH,
    val translationModel: TranslationModel? = null,
    val errorMessage: String? = null,
)
