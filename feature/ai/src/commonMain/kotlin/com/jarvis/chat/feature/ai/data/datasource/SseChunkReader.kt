package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.mapper.toChatStreamChunkDataModelOrNull
import com.jarvis.chat.feature.ai.data.model.ChatCompletionChunkResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatStreamChunkDataModel
import io.ktor.utils.io.ByteReadChannel
import io.ktor.utils.io.readLine
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.FlowCollector
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json

internal const val SSE_DATA_PREFIX = "data:"
private const val SSE_DONE_PAYLOAD = "[DONE]"

internal fun parseSseLine(line: String): SseEvent? {
    if (!line.startsWith(SSE_DATA_PREFIX)) {
        return null
    }
    val payload = line.removePrefix(SSE_DATA_PREFIX).trim()
    return when {
        payload.isEmpty() -> null
        payload == SSE_DONE_PAYLOAD -> SseEvent.Done
        else -> SseEvent.Data(payload)
    }
}

internal fun sseChunkFlow(
    channel: ByteReadChannel,
    json: Json,
    firstLine: String? = null,
): Flow<ChatStreamChunkDataModel> = flow {
    if (firstLine != null && emitSseLine(line = firstLine, json = json)) {
        return@flow
    }
    while (!channel.isClosedForRead) {
        val line = channel.readLine() ?: break
        if (emitSseLine(line = line, json = json)) {
            return@flow
        }
    }
}

private suspend fun FlowCollector<ChatStreamChunkDataModel>.emitSseLine(line: String, json: Json): Boolean =
    when (val event = parseSseLine(line)) {
        SseEvent.Done -> true
        is SseEvent.Data -> {
            event.payload.decodeChunkOrNull(json)
                ?.toChatStreamChunkDataModelOrNull()
                ?.let { chunk -> emit(chunk) }
            false
        }
        null -> false
    }

@Suppress("SwallowedException")
private fun String.decodeChunkOrNull(json: Json): ChatCompletionChunkResponseModel? =
    try {
        json.decodeFromString(ChatCompletionChunkResponseModel.serializer(), this)
    } catch (malformed: SerializationException) {
        null
    }
