package com.jarvis.chat.feature.ai.di

import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSource
import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSourceImpl
import com.jarvis.chat.feature.ai.data.repository.AiRepositoryImpl
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigProvider
import com.jarvis.chat.feature.ai.domain.model.DeepSeekPromptConfigModel
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageStreamUseCase
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageUseCase
import io.ktor.client.HttpClient
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import org.koin.core.module.Module
import org.koin.core.module.dsl.factoryOf
import org.koin.core.module.dsl.singleOf
import org.koin.dsl.bind
import org.koin.dsl.module

val aiModule: Module = module {
    single { provideDeepSeekJson() }
    single { provideDeepSeekHttpClient(json = get()) }
    single {
        val providerConfigProvider: AiProviderConfigProvider = get()
        DeepSeekPromptConfigModel(systemPrompt = providerConfigProvider.currentConfig().systemPrompt)
    }
    singleOf(::DeepSeekRemoteDataSourceImpl) bind DeepSeekRemoteDataSource::class
    singleOf(::AiRepositoryImpl) bind AiRepository::class
    factoryOf(::SendMessageUseCase)
    factoryOf(::SendMessageStreamUseCase)
}

private const val DEEP_SEEK_REQUEST_TIMEOUT_MILLIS = 90_000L
private const val DEEP_SEEK_CONNECT_TIMEOUT_MILLIS = 10_000L
private const val DEEP_SEEK_SOCKET_TIMEOUT_MILLIS = 60_000L

private fun provideDeepSeekJson(): Json =
    Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

private fun provideDeepSeekHttpClient(json: Json): HttpClient =
    HttpClient {
        expectSuccess = true
        install(ContentNegotiation) {
            json(json)
        }
        install(HttpTimeout) {
            requestTimeoutMillis = DEEP_SEEK_REQUEST_TIMEOUT_MILLIS
            connectTimeoutMillis = DEEP_SEEK_CONNECT_TIMEOUT_MILLIS
            socketTimeoutMillis = DEEP_SEEK_SOCKET_TIMEOUT_MILLIS
        }
        defaultRequest {
            contentType(ContentType.Application.Json)
        }
    }
