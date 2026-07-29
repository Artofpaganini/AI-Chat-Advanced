package com.jarvis.chat

import com.jarvis.chat.feature.ai.di.DeepSeekDefaults

data class AppConfig(
    val deepSeekApiKey: String,
    val deepSeekBaseUrl: String,
    val filesDirectoryPath: String,
    val localModelBaseUrl: String = DeepSeekDefaults.LOCAL_BASE_URL,
    val localModelAdapterPath: String = DeepSeekDefaults.LOCAL_MODEL_ADAPTER_PATH,
    val triageBaseUrl: String = DeepSeekDefaults.TRIAGE_BASE_URL,
)
