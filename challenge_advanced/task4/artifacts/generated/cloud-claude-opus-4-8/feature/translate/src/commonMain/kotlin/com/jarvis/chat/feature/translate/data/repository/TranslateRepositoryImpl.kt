package com.jarvis.chat.feature.translate.data.repository

import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSource
import com.jarvis.chat.feature.translate.data.mapper.toTranslationModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository

internal class TranslateRepositoryImpl(
    private val translateRemoteDataSource: TranslateRemoteDataSource,
) : TranslateRepository {

    override suspend fun translate(text: String, targetLanguage: TargetLanguage): TranslationModel =
        translateRemoteDataSource
            .translate(text = text, languageTitle = targetLanguage.title)
            .toTranslationModel(sourceText = text, targetLanguage = targetLanguage)
}
