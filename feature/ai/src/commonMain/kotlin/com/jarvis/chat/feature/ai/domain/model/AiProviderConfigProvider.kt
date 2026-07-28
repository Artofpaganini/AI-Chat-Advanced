package com.jarvis.chat.feature.ai.domain.model

fun interface AiProviderConfigProvider {

    fun currentConfig(): AiProviderConfigModel
}
