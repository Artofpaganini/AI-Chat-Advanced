package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.AppConfig
import com.jarvis.chat.feature.translate.data.model.TranslateMessageRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType

private const val CHAT_MODEL = "deepseek-chat"
private const val COMPLETIONS_PATH = "chat/completions"
private const val ROLE_SYSTEM = "system"
private const val ROLE_USER = "user"

internal class TranslateRemoteDataSourceImpl(
    private val httpClient: HttpClient,
    private val appConfig: AppConfig,
) : TranslateRemoteDataSource {

    override suspend fun translate(text: String, languageTitle: String): TranslateResponseModel {
        val requestModel = TranslateRequestModel(
            model = CHAT_MODEL,
            messages = listOf(
                TranslateMessageRequestModel(
                    role = ROLE_SYSTEM,
                    content = "Translate the user text into $languageTitle. Reply with the translation only.",
                ),
                TranslateMessageRequestModel(role = ROLE_USER, content = text),
            ),
        )
        return httpClient.post("${appConfig.deepSeekBaseUrl}$COMPLETIONS_PATH") {
            header(HttpHeaders.Authorization, "Bearer ${appConfig.deepSeekApiKey}")
            contentType(ContentType.Application.Json)
            setBody(requestModel)
        }.body()
    }
}
