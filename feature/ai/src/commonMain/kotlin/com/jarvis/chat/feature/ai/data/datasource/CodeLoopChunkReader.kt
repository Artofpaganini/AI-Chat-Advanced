package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.CodeLoopStageEventResponseModel
import io.ktor.utils.io.ByteReadChannel
import io.ktor.utils.io.readLine
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json

internal fun codeLoopStageEventFlow(
    channel: ByteReadChannel,
    json: Json,
): Flow<CodeLoopStageEventResponseModel> = flow {
    while (!channel.isClosedForRead) {
        val line = channel.readLine() ?: break
        when (val event = parseSseLine(line)) {
            SseEvent.Done -> return@flow
            is SseEvent.Data -> emit(json.decodeFromString(CodeLoopStageEventResponseModel.serializer(), event.payload))
            null -> Unit
        }
    }
}
