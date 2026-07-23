package com.jarvis.chat.feature.translate.domain.usecase

import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository

internal class TranslateTextUseCase(
    private val repository: TranslateRepository,
) {
    suspend operator fun invoke(text: String, targetLanguage: String): TranslationModel {
        return repository.translate(text, targetLanguage)
    }
}
