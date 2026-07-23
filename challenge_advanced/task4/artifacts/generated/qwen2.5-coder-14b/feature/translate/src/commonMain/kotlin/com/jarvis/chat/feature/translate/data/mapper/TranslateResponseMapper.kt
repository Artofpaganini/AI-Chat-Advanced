package com.jarvis.chat.feature.translate.data.mapper

import com.jarvis.chat.feature.translate.data.model.TranslateChoiceResponseModel
import com.jarvis.chat.feature.translate.data.model.TranslateMessageResponseModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal fun TranslateResponseModel.toTranslationModel(): TranslationModel =
    TranslationModel(
        sourceText = messages.firstOrNull()?.content.orEmpty(),
        translatedText = choices.firstOrNull()?.message?.content.orEmpty(),
    )
