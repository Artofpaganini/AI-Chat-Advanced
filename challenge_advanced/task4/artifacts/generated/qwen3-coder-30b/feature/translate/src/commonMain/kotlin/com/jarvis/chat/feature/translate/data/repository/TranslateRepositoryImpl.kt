package com.jarvis.chat.feature.translate.data.repository

import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSource
import com.jarvis.chat.feature.translate.data.mapper.toTranslationModel
import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository

internal class TranslateRepositoryImpl(
    private val remoteDataSource: TranslateRemoteDataSource,
) : TranslateRepository {
    override suspend fun translate(text: String, targetLanguage: String): TranslationModel {
        val request = TranslateRequestModel(
            messages = listOf(
                TranslateRequestModel.TranslateMessageRequestModel(
                    role = "user",
                    content = "Translate the following text to $targetLanguage: $text"
                )
            )
        )
        return remoteDataSource.translate(request).toTranslationModel()
    }
}
