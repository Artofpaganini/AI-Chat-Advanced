package com.jarvis.chat.feature.ai.data.datasource

internal sealed interface SseEvent {

    data class Data(val payload: String) : SseEvent

    data object Done : SseEvent
}
