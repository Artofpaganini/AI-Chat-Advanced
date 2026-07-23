package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.body
import kotlinx.serialization.json.Json

internal interface TranslateRemoteDataSource {
    suspend fun translateText(request: TranslateRequestModel): TranslateResponseModel
}

internal class TranslateRemoteDataSourceImpl(
    private val client: HttpClient,
    private val baseUrl: String,
    private val apiKey: String
) : TranslateRemoteDataSource {

    override suspend fun translateText(request: TranslateRequestModel): TranslateResponseModel {
        return client.post("$baseUrl/chat/completions") {
            setBody(Json.encodeToString(TranslateRequestModel.serializer(), request))
            header("Authorization", "Bearer $apiKey")
        }.body()
    }
}
