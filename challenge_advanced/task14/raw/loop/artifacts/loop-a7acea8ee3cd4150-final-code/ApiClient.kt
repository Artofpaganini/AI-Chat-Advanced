package com.jarvis.chat.feature.loopgenerated

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.get
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

private const val BASE_URL = "https://api.example.com"
private const val DATA_PATH = "/data"

@Serializable
internal data class ApiResponse(
    @SerialName("id")
    val id: String,
    @SerialName("value")
    val value: String,
)

internal object ApiClient {
    private val client = HttpClient {
        install(ContentNegotiation) {
            json(
                Json {
                    ignoreUnknownKeys = true
                },
            )
        }
    }

    suspend fun fetchData(): ApiResponse {
        return client.get("$BASE_URL$DATA_PATH").body()
    }
}
