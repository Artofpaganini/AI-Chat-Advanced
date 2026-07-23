package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.AppConfig
import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import io.ktor.client.HttpClient
import io.ktor.client.request.headers
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType

internal class TranslateRemoteDataSourceImpl(
    private val client: HttpClient,
    private val appConfig: AppConfig,
) : TranslateRemoteDataSource {
    override suspend fun translate(request: TranslateRequestModel): TranslateResponseModel {
        return client.post("${appConfig.deepSeekBaseUrl}/chat/completions") {
            headers {
                append(HttpHeaders.Authorization, "Bearer ${appConfig.deepSeekApiKey}")
                contentType(ContentType.Application.Json)
            }
            setBody(request)
        }.body()
    }
}
