package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.AppConfig
import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.body

internal class TranslateRemoteDataSourceImpl(
    private val client: HttpClient,
    private val appConfig: AppConfig,
) : TranslateRemoteDataSource {

    override suspend fun translate(request: TranslateRequestModel): TranslateResponseModel {
        return client.post("${appConfig.deepSeekBaseUrl}/chat/completions") {
            setBody(request)
            headers.append("Authorization", "Bearer ${appConfig.deepSeekApiKey}")
        }.body()
    }
}
