package com.jarvis.chat.feature.chat.domain.mapper

import com.jarvis.chat.feature.ai.domain.model.CodeLoopErrorModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopRunModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageEventModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStatusModel
import kotlin.test.Test
import kotlin.test.assertTrue

class CodeLoopReplyMapperTest {

    @Test
    fun toReplyText_onCommitReached_containsCommitHashAndCodeFence() {
        val runModel = runModel(
            commit = "a1b2c3d",
            finalCode = mapOf("TokenStorage.kt" to "class TokenStorage"),
        )

        val text = runModel.toReplyText()

        assertTrue(text.contains("a1b2c3d"))
        assertTrue(text.contains("```kotlin"))
        assertTrue(text.contains("class TokenStorage"))
    }

    @Test
    fun toReplyText_onStuckWithoutCommit_namesLastStagePlainly() {
        val runModel = runModel(
            commit = null,
            events = listOf(
                stageEvent(stage = CodeLoopStageModel.SECURITY, status = CodeLoopStatusModel.FAILED, iteration = 2),
                stageEvent(stage = CodeLoopStageModel.RESULT, status = CodeLoopStatusModel.DONE),
            ),
        )

        val text = runModel.toReplyText()

        assertTrue(text.contains("без коммита"))
        assertTrue(text.contains("SECURITY"))
        assertTrue(text.contains("итерация 2"))
    }

    @Test
    fun toReplyText_onServerUnavailable_namesTheAddress() {
        val runModel = runModel(error = CodeLoopErrorModel.ServerUnavailable(address = "http://10.0.2.2:8092/"))

        val text = runModel.toReplyText()

        assertTrue(text.contains("не запущен"))
        assertTrue(text.contains("http://10.0.2.2:8092/"))
    }

    @Test
    fun toReplyText_onMalformedResponse_namesTheDetail() {
        val runModel = runModel(error = CodeLoopErrorModel.MalformedResponse(detail = "unexpected field"))

        val text = runModel.toReplyText()

        assertTrue(text.contains("неожиданном формате"))
        assertTrue(text.contains("unexpected field"))
    }

    @Test
    fun toReplyText_onInterruptedMidRun_namesLastStageAndIteration() {
        val runModel = runModel(
            error = CodeLoopErrorModel.InterruptedMidRun(lastStage = CodeLoopStageModel.BUILD, lastIteration = 2),
        )

        val text = runModel.toReplyText()

        assertTrue(text.contains("прервался"))
        assertTrue(text.contains("BUILD"))
        assertTrue(text.contains("итерация 2"))
    }

    private fun runModel(
        commit: String? = null,
        finalCode: Map<String, String> = emptyMap(),
        events: List<CodeLoopStageEventModel> = emptyList(),
        error: CodeLoopErrorModel? = null,
    ): CodeLoopRunModel =
        CodeLoopRunModel(
            task = "task",
            events = events,
            isRunning = false,
            commit = commit,
            iterationsUsed = 1,
            securityFindingsTotal = 0,
            gatewayBlocksTotal = 0,
            finalCode = finalCode,
            error = error,
        )

    private fun stageEvent(
        stage: CodeLoopStageModel,
        status: CodeLoopStatusModel,
        iteration: Int? = null,
    ): CodeLoopStageEventModel =
        CodeLoopStageEventModel(
            stage = stage,
            iteration = iteration,
            status = status,
            files = emptyList(),
            gatewayVerdict = null,
            errors = emptyList(),
            findings = emptyList(),
            commit = null,
            iterationsUsed = null,
            securityFindings = null,
            gatewayBlocks = null,
            finalCode = emptyMap(),
        )
}
