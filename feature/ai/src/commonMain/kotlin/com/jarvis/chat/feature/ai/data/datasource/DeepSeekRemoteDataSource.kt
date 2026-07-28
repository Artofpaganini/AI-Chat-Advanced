package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import com.jarvis.chat.feature.ai.data.model.ChatStreamChunkDataModel
import kotlinx.coroutines.flow.Flow

internal interface DeepSeekRemoteDataSource {

    suspend fun requestCompletion(
        messages: List<ChatMessageRequestModel>,
    ): ChatCompletionResponseModel

    fun requestCompletionStream(
        messages: List<ChatMessageRequestModel>,
    ): Flow<ChatStreamChunkDataModel>
}
