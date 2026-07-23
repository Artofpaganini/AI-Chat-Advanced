package com.jarvis.chat.feature.translate.data.datasource

import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.request.url
import kotlinx.serialization.json.JsonObject

internal interface TranslateRemoteDataSource {
    suspend fun translate(text: String, targetLanguage: String): JsonObject?
}

internal class TranslateRemoteDataSourceImpl(private val client: HttpClient) : TranslateRemoteDataSource {
    override suspend fun translate(text: String, targetLanguage: String): JsonObject? {
        val requestModel = com.jarvis.chat.feature.translate.data.model.TranslateRequestModel(sourceText = text, targetLanguage = targetLanguage)
        return client.post("${AppConfig.deepSeekBaseUrl}/chat/completions") {
            setBody(requestModel)
        }.body()
    }
}
