package com.jarvis.chat.feature.translate.domain.repository

import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal interface TranslateRepository {
    suspend fun translateText(sourceText: String, targetLanguage: TargetLanguage): TranslationModel
}
