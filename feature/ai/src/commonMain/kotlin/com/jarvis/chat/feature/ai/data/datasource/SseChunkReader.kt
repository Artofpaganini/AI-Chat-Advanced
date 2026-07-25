package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.mapper.toDeltaTextOrNull
import com.jarvis.chat.feature.ai.data.model.ChatCompletionChunkResponseModel
import io.ktor.utils.io.ByteReadChannel
import io.ktor.utils.io.readLine
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json

private const val SSE_DATA_PREFIX = "data:"
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

internal fun sseChunkTextFlow(channel: ByteReadChannel, json: Json): Flow<String> = flow {
    while (!channel.isClosedForRead) {
        val line = channel.readLine() ?: break
        when (val event = parseSseLine(line)) {
            SseEvent.Done -> return@flow
            is SseEvent.Data -> event.payload.decodeDeltaTextOrNull(json)?.let { text -> emit(text) }
            null -> Unit
        }
    }
}

@Suppress("SwallowedException")
private fun String.decodeDeltaTextOrNull(json: Json): String? =
    try {
        json.decodeFromString(ChatCompletionChunkResponseModel.serializer(), this).toDeltaTextOrNull()
    } catch (malformed: SerializationException) {
        null
    }
