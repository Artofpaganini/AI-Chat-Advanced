package com.jarvis.chat.feature.ai.domain.model

fun interface GatewayConfigProvider {

    fun currentRootUrl(): String
}
