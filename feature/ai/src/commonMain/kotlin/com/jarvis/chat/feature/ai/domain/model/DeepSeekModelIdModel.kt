package com.jarvis.chat.feature.ai.domain.model

import com.jarvis.chat.feature.ai.di.DeepSeekDefaults

enum class DeepSeekModelIdModel(val apiId: String) {
    FLASH(DeepSeekDefaults.CHAT_MODEL),
    PRO(DeepSeekDefaults.CHAT_MODEL_PRO),
}
