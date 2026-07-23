package com.jarvis.chat.feature.translate.data.mapper

import com.jarvis.chat.feature.translate.data.model.TranslateChoiceResponseModel
import com.jarvis.chat.feature.translate.data.model.TranslateMessageResponseModel
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage

internal fun TranslateChoiceResponseModel?.toTranslationModel(): TranslationModel {
    val content = this?.message?.content ?: ""
    return TranslationModel(sourceText = content, translatedText = content)
}
