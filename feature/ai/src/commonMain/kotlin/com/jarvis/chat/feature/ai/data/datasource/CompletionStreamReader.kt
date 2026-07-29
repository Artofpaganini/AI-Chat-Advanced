package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.mapper.toChatStreamChunkDataModel
import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatStreamChunkDataModel
import io.ktor.utils.io.ByteReadChannel
import io.ktor.utils.io.readLine
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emitAll
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json

internal fun completionStreamChunkFlow(
    channel: ByteReadChannel,
    json: Json,
): Flow<ChatStreamChunkDataModel> = flow {
    val firstLine = channel.readLine() ?: return@flow
    if (firstLine.startsWith(SSE_DATA_PREFIX)) {
        emitAll(sseChunkFlow(channel = channel, json = json, firstLine = firstLine))
    } else {
        emit(channel.readFullResponse(firstLine = firstLine, json = json).toChatStreamChunkDataModel())
    }
}

private suspend fun ByteReadChannel.readFullResponse(firstLine: String, json: Json): ChatCompletionResponseModel {
    val body = StringBuilder(firstLine)
    while (!isClosedForRead) {
        val line = readLine() ?: break
        body.append(line)
    }
    return json.decodeFromString(ChatCompletionResponseModel.serializer(), body.toString())
}
