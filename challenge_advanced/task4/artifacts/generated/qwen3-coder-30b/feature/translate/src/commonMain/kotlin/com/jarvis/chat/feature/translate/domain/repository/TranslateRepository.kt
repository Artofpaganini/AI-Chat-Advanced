package com.jarvis.chat.feature.translate.domain.repository

import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage

internal interface TranslateRepository {
    suspend fun translate(text: String, targetLanguage: String): TranslationModel
}
