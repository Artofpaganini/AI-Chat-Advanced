package com.jarvis.chat.di

import com.jarvis.chat.AppConfig
import com.jarvis.chat.feature.ai.domain.model.DeepSeekConfigModel
import com.jarvis.chat.feature.chat.di.chatModule
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
                single { DeepSeekConfigModel(apiKey = appConfig.deepSeekApiKey) }
            },
            chatModule,
        )
    }
}
