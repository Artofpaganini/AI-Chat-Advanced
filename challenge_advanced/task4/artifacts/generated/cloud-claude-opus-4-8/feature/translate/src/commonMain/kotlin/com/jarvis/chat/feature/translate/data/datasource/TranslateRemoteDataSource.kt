package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel

internal interface TranslateRemoteDataSource {

    suspend fun translate(text: String, languageTitle: String): TranslateResponseModel
}
