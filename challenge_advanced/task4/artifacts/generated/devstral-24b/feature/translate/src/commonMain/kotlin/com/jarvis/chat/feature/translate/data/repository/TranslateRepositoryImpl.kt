package com.jarvis.chat.feature.translate.data.repository

import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSource
import com.jarvis.chat.feature.translate.data.mapper.toTranslationModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository

internal class TranslateRepositoryImpl(
    private val remoteDataSource: TranslateRemoteDataSource
) : TranslateRepository {

    override suspend fun translateText(sourceText: String, targetLanguage: TargetLanguage): TranslationModel {
        val request = TranslateRequestModel(
            model = "deepseek-chat",
            messages = listOf(TranslateMessageRequestModel(role = "user", content = sourceText))
        )
        val response = remoteDataSource.translateText(request)
        return response.toTranslationModel()
    }
}
