package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.body

internal interface TranslateRemoteDataSource {
    suspend fun translate(request: TranslateRequestModel): TranslateResponseModel
}
