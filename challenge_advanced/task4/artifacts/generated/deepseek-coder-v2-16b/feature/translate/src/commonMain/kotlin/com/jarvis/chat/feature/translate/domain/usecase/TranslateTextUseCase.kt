package com.jarvis.chat.feature.translate.domain.usecase

import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

internal class TranslateTextUseCase(private val repository: TranslateRepository) {
    operator fun invoke(text: String, targetLanguage: TargetLanguage): Flow<TranslationModel> = repository.translateText(text, targetLanguage).map { it }
}
