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
    fun sseChunkFlow_onNormalChunks_emitsDeltaContentInOrder() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: {"choices":[{"delta":{"content":"lo"}}]}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("Hel", "lo"), chunks.map { chunk -> chunk.text })
    }

    @Test
    fun sseChunkFlow_onDoneMarker_stopsEmittingFurtherChunks() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: [DONE]

            data: {"choices":[{"delta":{"content":"after done"}}]}

        """.trimIndent()

        val chunks = sseChunkFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("Hel"), chunks.map { chunk -> chunk.text })
    }

    @Test
    fun sseChunkFlow_onMalformedJson_skipsAndContinues() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: {broken json

            data: {"choices":[{"delta":{"content":"lo"}}]}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("Hel", "lo"), chunks.map { chunk -> chunk.text })
    }

    @Test
    fun sseChunkFlow_onEmptyDeltaContentAndNoModel_isSkipped() = runTest {
        val sse = """
            data: {"choices":[{"delta":{}}]}

            data: {"choices":[{"delta":{"content":""}}]}

            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("Hel"), chunks.map { chunk -> chunk.text })
    }

    @Test
    fun sseChunkFlow_onChunksCarryingModel_capturesModelIdAlongsideText() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"content":"Hel"}}],"model":"deepseek-chat"}

            data: {"choices":[{"delta":{"content":"lo"}}],"model":"deepseek-chat"}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("deepseek-chat", "deepseek-chat"), chunks.map { chunk -> chunk.modelId })
    }

    @Test
    fun sseChunkFlow_onFinalChunkCarryingOnlyTriage_stillEmitsTriage() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"triage":{"route":"EMERGENCY","status":"OK"}}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf(null, "EMERGENCY"), chunks.map { chunk -> chunk.triage?.route })
    }

    @Test
    fun sseChunkFlow_onModelOnlyChunkWithoutDeltaContent_stillEmitsModelId() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"role":"assistant"}}],"model":"deepseek-chat"}

            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("" to "deepseek-chat", "Hel" to null), chunks.map { chunk -> chunk.text to chunk.modelId })
    }

    @Test
    fun sseChunkFlow_onOutputTruncationEventBeforeDone_emitsChunkCarryingTruncation() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: {"gateway_output_verdict":"blocked_output","gateway_output_reasons":["dangerous_command"],"gateway_truncated_at_chars":12}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("Hel", ""), chunks.map { chunk -> chunk.text })
        assertNull(chunks[0].outputTruncation)
        assertEquals("blocked_output", chunks[1].outputTruncation?.verdict)
        assertEquals(listOf("dangerous_command"), chunks[1].outputTruncation?.reasons)
        assertEquals(12, chunks[1].outputTruncation?.truncatedAtChars)
    }

    @Test
    fun sseChunkFlow_onNormalChunk_neverMistakenForOutputTruncationEvent() = runTest {
        val sse = """
            data: {"choices":[{"delta":{"content":"Hel"}}]}

            data: [DONE]

        """.trimIndent()

        val chunks = sseChunkFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf(null), chunks.map { chunk -> chunk.outputTruncation })
    }

    private val testJson: Json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }
}
