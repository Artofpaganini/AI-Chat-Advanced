package com.jarvis.chat.feature.translate.domain.repository

import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import kotlinx.coroutines.flow.Flow

internal interface TranslateRepository {
    suspend fun translateText(text: String, targetLanguage: TargetLanguage): Flow<TranslationModel>
}
