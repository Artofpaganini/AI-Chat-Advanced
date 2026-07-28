package com.jarvis.chat.feature.ai.domain.model

data class AiProviderConfigModel(
    val baseUrl: String,
    val modelId: String,
    val systemPrompt: String,
    val isApiKeyRequired: Boolean,
    val adapterPath: String? = null,
    val maxTokens: Int? = null,
    val temperature: Double? = null,
    val repetitionPenalty: Double? = null,
)
