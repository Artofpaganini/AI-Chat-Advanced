package com.jarvis.chat.feature.translate.data.repository

import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSource
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

internal class TranslateRepositoryImpl(private val dataSource: TranslateRemoteDataSource) : TranslateRepository {
    override suspend fun translateText(text: String, targetLanguage: TargetLanguage): Flow<TranslationModel> = flow {
        val response = dataSource.translate(text, targetLanguage.name) ?: throw NetworkErrorException()
        emit(response.toTranslationModel())
    }
}
