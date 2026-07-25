package com.jarvis.chat.feature.ai.domain.model

fun interface DeepSeekModelProvider {

    fun currentModel(): String
}
