package com.jarvis.chat.feature.translate.domain.usecase

import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository

internal class TranslateTextUseCase(
    private val repository: TranslateRepository
) {
    suspend operator fun invoke(sourceText: String, targetLanguage: TargetLanguage): TranslationModel {
        return repository.translateText(sourceText, targetLanguage)
    }
}
