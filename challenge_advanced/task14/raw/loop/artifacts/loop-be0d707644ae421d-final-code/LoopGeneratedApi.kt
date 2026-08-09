package com.jarvis.chat.feature.loopgenerated

import io.ktor.client.HttpClient
import io.ktor.client.request.get
import io.ktor.client.statement.bodyAsText

internal class LoopGeneratedApi(
    private val client: HttpClient
) {
    suspend fun fetchData(): String = client.get(API_URL).bodyAsText()

    private companion object {
        const val API_URL: String = "https://api.example.com/data"
    }
}
