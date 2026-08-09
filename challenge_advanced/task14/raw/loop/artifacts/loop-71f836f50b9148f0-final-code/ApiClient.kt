package com.jarvis.chat.feature.loopgenerated

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

internal class ApiClient {
    private val client = HttpClient {
        install(ContentNegotiation) {
            json(
                Json {
                    ignoreUnknownKeys = true
                }
            )
        }
    }

    suspend inline fun <reified Response> get(
        url: String,
    ): Response = client.get(url).body()

    suspend inline fun <reified Request, reified Response> post(
        url: String,
        request: Request,
    ): Response = client.post(url) {
        contentType(ContentType.Application.Json)
        setBody(request)
    }.body()
}
