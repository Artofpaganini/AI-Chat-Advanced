package com.jarvis.chat.feature.translate.data.mapper

import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal fun TranslateResponseModel.toTranslationModel(): TranslationModel {
    val translatedText = choices.firstOrNull()?.message?.content.orEmpty()
    return TranslationModel(sourceText = "", translatedText = translatedText)
}
