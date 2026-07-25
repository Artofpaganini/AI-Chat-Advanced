package com.jarvis.chat.di

import com.jarvis.chat.AppConfig
import com.jarvis.chat.feature.ai.domain.model.DeepSeekConfigModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekModelIdModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekModelProvider
import com.jarvis.chat.feature.chat.di.chatModule
import com.jarvis.chat.feature.settings.di.settingsModule
import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import com.jarvis.chat.feature.settings.domain.usecase.ObserveAiModelUseCase
import org.koin.core.context.startKoin
import org.koin.dsl.module
import org.koin.mp.KoinPlatform

fun initKoin(appConfig: AppConfig) {
    if (KoinPlatform.getKoinOrNull() != null) {
        return
    }
    startKoin {
        modules(
            module {
                single { appConfig }
                single {
                    DeepSeekConfigModel(
                        apiKey = appConfig.deepSeekApiKey,
                        baseUrl = appConfig.deepSeekBaseUrl,
                    )
                }
                single<DeepSeekModelProvider> {
                    val observeAiModelUseCase: ObserveAiModelUseCase = get()
                    DeepSeekModelProvider { observeAiModelUseCase().value.toDeepSeekModelId() }
                }
            },
            chatModule(storageDirectoryPath = appConfig.filesDirectoryPath),
            settingsModule,
        )
    }
}

private fun AiModelModel.toDeepSeekModelId(): String =
    when (this) {
        AiModelModel.FLASH -> DeepSeekModelIdModel.FLASH.apiId
        AiModelModel.PRO -> DeepSeekModelIdModel.PRO.apiId
    }
