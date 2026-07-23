package com.jarvis.chat.feature.translate.data.mapper

import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal fun TranslateResponseModel.toTranslationModel(
    sourceText: String,
    targetLanguage: TargetLanguage,
): TranslationModel =
    TranslationModel(
        sourceText = sourceText,
        translatedText = choices.firstOrNull()?.message?.content.orEmpty().trim(),
        targetLanguage = targetLanguage,
    )
