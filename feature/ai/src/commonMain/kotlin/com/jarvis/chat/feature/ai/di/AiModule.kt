package com.jarvis.chat.feature.ai.di

import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSource
import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSourceImpl
import com.jarvis.chat.feature.ai.data.repository.AiRepositoryImpl
import com.jarvis.chat.feature.ai.domain.model.DeepSeekConfigModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekPromptConfigModel
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageUseCase
import io.ktor.client.HttpClient
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.request.header
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import org.koin.core.module.Module
import org.koin.core.module.dsl.factoryOf
import org.koin.core.module.dsl.singleOf
import org.koin.dsl.bind
import org.koin.dsl.module

val aiModule: Module = module {
    single { provideDeepSeekHttpClient(config = get()) }
    single {
        DeepSeekPromptConfigModel(
            model = DeepSeekDefaults.CHAT_MODEL,
            systemPrompt = DeepSeekDefaults.SYSTEM_PROMPT,
        )
    }
    singleOf(::DeepSeekRemoteDataSourceImpl) bind DeepSeekRemoteDataSource::class
    singleOf(::AiRepositoryImpl) bind AiRepository::class
    factoryOf(::SendMessageUseCase)
}

private const val DEEP_SEEK_REQUEST_TIMEOUT_MILLIS = 90_000L
private const val DEEP_SEEK_CONNECT_TIMEOUT_MILLIS = 10_000L
private const val DEEP_SEEK_SOCKET_TIMEOUT_MILLIS = 60_000L

private fun provideDeepSeekHttpClient(config: DeepSeekConfigModel): HttpClient =
    HttpClient {
        install(ContentNegotiation) {
            json(
                Json {
                    ignoreUnknownKeys = true
                    isLenient = true
                },
            )
        }
        install(HttpTimeout) {
            requestTimeoutMillis = DEEP_SEEK_REQUEST_TIMEOUT_MILLIS
            connectTimeoutMillis = DEEP_SEEK_CONNECT_TIMEOUT_MILLIS
            socketTimeoutMillis = DEEP_SEEK_SOCKET_TIMEOUT_MILLIS
        }
        defaultRequest {
            url(config.baseUrl)
            header(HttpHeaders.Authorization, "Bearer ${config.apiKey}")
            contentType(ContentType.Application.Json)
        }
    }
