package com.jarvis.chat.feature.ai.data.datasource

import io.ktor.utils.io.ByteReadChannel
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class CodeLoopChunkReaderTest {

    @Test
    fun codeLoopStageEventFlow_onNormalEvents_emitsEachEventInOrder() = runTest {
        val sse = """
            data: {"stage":"GENERATE","iteration":1,"status":"running"}

            data: {"stage":"GENERATE","iteration":1,"status":"done","files":["TokenStorage.kt"],"gateway_verdict":"pass"}

            data: {"stage":"COMMIT","iteration":1,"status":"done","commit":"a1b2c3d"}

        """.trimIndent()

        val events = codeLoopStageEventFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(listOf("GENERATE", "GENERATE", "COMMIT"), events.map { event -> event.stage })
        assertEquals("a1b2c3d", events.last().commit)
    }

    @Test
    fun codeLoopStageEventFlow_onMalformedJson_throwsInsteadOfSkipping() = runTest {
        val sse = """
            data: {"stage":"GENERATE","iteration":1,"status":"running"}

            data: {broken json

        """.trimIndent()

        assertFailsWith<SerializationException> {
            codeLoopStageEventFlow(channel = ByteReadChannel(sse), json = testJson).toList()
        }
    }

    @Test
    fun codeLoopStageEventFlow_onChannelClosedWithoutDoneMarker_completesNormally() = runTest {
        val sse = """
            data: {"stage":"RESULT","status":"done","iterations_used":3,"security_findings":4,"gateway_blocks":1}

        """.trimIndent()

        val events = codeLoopStageEventFlow(channel = ByteReadChannel(sse), json = testJson).toList()

        assertEquals(1, events.size)
        assertEquals("RESULT", events.single().stage)
        assertEquals(3, events.single().iterationsUsed)
    }

    private val testJson: Json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }
}
