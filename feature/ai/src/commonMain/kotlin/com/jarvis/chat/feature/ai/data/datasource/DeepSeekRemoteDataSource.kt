package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel

internal interface DeepSeekRemoteDataSource {

    suspend fun requestCompletion(
        messages: List<ChatMessageRequestModel>,
    ): ChatCompletionResponseModel
}
