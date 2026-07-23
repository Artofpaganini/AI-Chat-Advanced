package com.jarvis.chat.feature.translate.domain.usecase

import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository

internal class TranslateTextUseCase(
    private val translateRepository: TranslateRepository,
) {

    suspend operator fun invoke(text: String, targetLanguage: TargetLanguage): TranslationModel =
        translateRepository.translate(text = text, targetLanguage = targetLanguage)
}
