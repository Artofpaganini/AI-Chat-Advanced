package com.jarvis.chat.feature.ai.data.datasource

import io.ktor.utils.io.ByteReadChannel
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class SseChunkReaderTest {

    @Test
    fun parseSseLine_onNormalDataLine_returnsDataEventWithPayload() {
        val event = parseSseLine("data: {\"choices\":[]}")

        assertEquals(SseEvent.Data(payload = "{\"choices\":[]}"), event)
    }

    @Test
    fun parseSseLine_onDataLineWithoutSpaceAfterColon_stillParses() {
        val event = parseSseLine("data:{\"choices\":[]}")

        assertEquals(SseEvent.Data(payload = "{\"choices\":[]}"), event)
    }

    @Test
    fun parseSseLine_onDoneMarker_returnsDone() {
        val event = parseSseLine("data: [DONE]")

        assertEquals(SseEvent.Done, event)
    }

    @Test
    fun parseSseLine_onBlankLine_returnsNull() {
        val event = parseSseLine("")

        assertNull(event)
    }

    @Test
    fun parseSseLine_onNonDataLine_returnsNull() {
        val event = parseSseLine("event: ping")

        assertNull(event)
    }

    @Test
    fun parseSseLine_onEmptyDataPayload_returnsNull() {
        val event = parseSseLine("data:")

        assertNull(event)
    }

    @Test
    fun sseChunkTextFlow_onNormalChunks_emitsDeltaContentInOrder() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: {"choices":[{"delta":{"content":"lo"}}]}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkTextFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("Hel", "lo"), chunks)
    }

    @Test
    fun sseChunkTextFlow_onDoneMarker_stopsEmittingFurtherChunks() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: [DONE]

            data: {"choices":[{"delta":{"content":"after done"}}]}

        """.trimIndent()

        val chunks = sseChunkTextFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("Hel"), chunks)
    }

    @Test
    fun sseChunkTextFlow_onMalformedJson_skipsAndContinues() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: {broken json

            data: {"choices":[{"delta":{"content":"lo"}}]}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkTextFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("Hel", "lo"), chunks)
    }

    @Test
    fun sseChunkTextFlow_onEmptyDeltaContent_isSkipped() = runTest {
        val sse = """
            data: {"choices":[{"delta":{}}]}

            data: {"choices":[{"delta":{"content":""}}]}

            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkTextFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("Hel"), chunks)
    }

    private val testJson: Json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }
}
