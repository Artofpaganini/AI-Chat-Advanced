package com.jarvis.chat.feature.ai.di

import com.jarvis.chat.feature.ai.data.datasource.CodeLoopRemoteDataSource
import com.jarvis.chat.feature.ai.data.datasource.CodeLoopRemoteDataSourceImpl
import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSource
import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSourceImpl
import com.jarvis.chat.feature.ai.data.datasource.GatewayRemoteDataSource
import com.jarvis.chat.feature.ai.data.datasource.GatewayRemoteDataSourceImpl
import com.jarvis.chat.feature.ai.data.repository.AiRepositoryImpl
import com.jarvis.chat.feature.ai.data.repository.CodeLoopRepositoryImpl
import com.jarvis.chat.feature.ai.data.repository.GatewayRepositoryImpl
import com.jarvis.chat.feature.ai.data.repository.InputGuardRepositoryImpl
import com.jarvis.chat.feature.ai.data.repository.MultiStageAiRepositoryImpl
import com.jarvis.chat.feature.ai.data.repository.OutputGuardRepositoryImpl
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigProvider
import com.jarvis.chat.feature.ai.domain.model.DeepSeekPromptConfigModel
import com.jarvis.chat.feature.ai.domain.repository.AiRepository
import com.jarvis.chat.feature.ai.domain.repository.CodeLoopRepository
import com.jarvis.chat.feature.ai.domain.repository.GatewayRepository
import com.jarvis.chat.feature.ai.domain.repository.InputGuardRepository
import com.jarvis.chat.feature.ai.domain.repository.MultiStageAiRepository
import com.jarvis.chat.feature.ai.domain.repository.OutputGuardRepository
import com.jarvis.chat.feature.ai.domain.usecase.CheckInputGuardUseCase
import com.jarvis.chat.feature.ai.domain.usecase.CheckOutputGuardUseCase
import com.jarvis.chat.feature.ai.domain.usecase.GetGatewayAuditUseCase
import com.jarvis.chat.feature.ai.domain.usecase.GetGatewayStatsUseCase
import com.jarvis.chat.feature.ai.domain.usecase.RunCodeLoopUseCase
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageStreamUseCase
import com.jarvis.chat.feature.ai.domain.usecase.SendMessageUseCase
import com.jarvis.chat.feature.ai.domain.usecase.SendMultiStageMessageUseCase
import io.github.aakira.napier.DebugAntilog
import io.github.aakira.napier.Napier
import io.ktor.client.HttpClient
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logger
import io.ktor.client.plugins.logging.Logging
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

internal val aiModule: Module = module {
    single { provideDeepSeekJson() }
    single { provideDeepSeekHttpClient(json = get()) }
    single {
        val providerConfigProvider: AiProviderConfigProvider = get()
        DeepSeekPromptConfigModel(systemPrompt = providerConfigProvider.currentConfig().systemPrompt)
    }
    singleOf(::DeepSeekRemoteDataSourceImpl) bind DeepSeekRemoteDataSource::class
    singleOf(::GatewayRemoteDataSourceImpl) bind GatewayRemoteDataSource::class
    singleOf(::CodeLoopRemoteDataSourceImpl) bind CodeLoopRemoteDataSource::class
    singleOf(::AiRepositoryImpl) bind AiRepository::class
    singleOf(::GatewayRepositoryImpl) bind GatewayRepository::class
    singleOf(::MultiStageAiRepositoryImpl) bind MultiStageAiRepository::class
    singleOf(::InputGuardRepositoryImpl) bind InputGuardRepository::class
    singleOf(::OutputGuardRepositoryImpl) bind OutputGuardRepository::class
    singleOf(::CodeLoopRepositoryImpl) bind CodeLoopRepository::class
    factoryOf(::SendMessageUseCase)
    factoryOf(::SendMessageStreamUseCase)
    factoryOf(::SendMultiStageMessageUseCase)
    factoryOf(::CheckInputGuardUseCase)
    factoryOf(::CheckOutputGuardUseCase)
    factoryOf(::GetGatewayAuditUseCase)
    factoryOf(::GetGatewayStatsUseCase)
    factoryOf(::RunCodeLoopUseCase)
}

internal const val DEEP_SEEK_REQUEST_TIMEOUT_MILLIS = 90_000L
internal const val DEEP_SEEK_CONNECT_TIMEOUT_MILLIS = 10_000L
internal const val DEEP_SEEK_SOCKET_TIMEOUT_MILLIS = 60_000L
internal const val DEEP_SEEK_HTTP_LOG_TAG = "DeepSeekHttp"

internal fun provideDeepSeekJson(): Json =
    Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

internal fun provideDeepSeekHttpClient(json: Json): HttpClient {
    Napier.base(DebugAntilog())
    return HttpClient {
        expectSuccess = true
        install(ContentNegotiation) {
            json(json)
        }
        install(HttpTimeout) {
            requestTimeoutMillis = DEEP_SEEK_REQUEST_TIMEOUT_MILLIS
            connectTimeoutMillis = DEEP_SEEK_CONNECT_TIMEOUT_MILLIS
            socketTimeoutMillis = DEEP_SEEK_SOCKET_TIMEOUT_MILLIS
        }
        install(Logging) {
            logger = object : Logger {
                override fun log(message: String) {
                    Napier.d(tag = DEEP_SEEK_HTTP_LOG_TAG) { message }
                }
            }
            level = LogLevel.ALL
            sanitizeHeader { header -> header == HttpHeaders.Authorization }
        }
        defaultRequest {
            contentType(ContentType.Application.Json)
        }
    }
}
