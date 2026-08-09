package com.jarvis.chat.feature.ai.domain.mapper

import com.jarvis.chat.feature.ai.domain.model.CodeLoopErrorModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageEventModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStatusModel
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class CodeLoopRunAccumulatorMapperTest {

    @Test
    fun toCodeLoopRunModel_whileNoResultEventYet_isRunningTrue() {
        val events = listOf(stageEvent(stage = CodeLoopStageModel.GENERATE, status = CodeLoopStatusModel.RUNNING))

        val runModel = events.toCodeLoopRunModel(task = "task")

        assertTrue(runModel.isRunning)
        assertNull(runModel.commit)
    }

    @Test
    fun toCodeLoopRunModel_onSuccessfulCommit_derivesCommitHash() {
        val events = listOf(
            stageEvent(stage = CodeLoopStageModel.COMMIT, status = CodeLoopStatusModel.DONE, commit = "a1b2c3d"),
            stageEvent(stage = CodeLoopStageModel.RESULT, status = CodeLoopStatusModel.DONE, iterationsUsed = 1),
        )

        val runModel = events.toCodeLoopRunModel(task = "task")

        assertFalse(runModel.isRunning)
        assertEquals("a1b2c3d", runModel.commit)
        assertEquals(1, runModel.iterationsUsed)
    }

    @Test
    fun toCodeLoopRunModel_onStuckWithoutCommit_commitIsNull() {
        val events = listOf(
            stageEvent(stage = CodeLoopStageModel.SECURITY, status = CodeLoopStatusModel.FAILED),
            stageEvent(stage = CodeLoopStageModel.RESULT, status = CodeLoopStatusModel.DONE, iterationsUsed = 3),
        )

        val runModel = events.toCodeLoopRunModel(task = "task")

        assertNull(runModel.commit)
        assertFalse(runModel.isRunning)
    }

    @Test
    fun toCodeLoopRunModel_onResultCarryingFinalCode_exposesFileContents() {
        val events = listOf(
            stageEvent(
                stage = CodeLoopStageModel.RESULT,
                status = CodeLoopStatusModel.DONE,
                finalCode = mapOf("TokenStorage.kt" to "class TokenStorage"),
            ),
        )

        val runModel = events.toCodeLoopRunModel(task = "task")

        assertEquals(mapOf("TokenStorage.kt" to "class TokenStorage"), runModel.finalCode)
    }

    @Test
    fun toCodeLoopRunModel_onError_isRunningFalseRegardlessOfEvents() {
        val events = listOf(stageEvent(stage = CodeLoopStageModel.GENERATE, status = CodeLoopStatusModel.RUNNING))

        val runModel = events.toCodeLoopRunModel(
            task = "task",
            error = CodeLoopErrorModel.ServerUnavailable(address = "http://10.0.2.2:8092/"),
        )

        assertFalse(runModel.isRunning)
        assertEquals(CodeLoopErrorModel.ServerUnavailable(address = "http://10.0.2.2:8092/"), runModel.error)
    }

    private fun stageEvent(
        stage: CodeLoopStageModel,
        status: CodeLoopStatusModel,
        iteration: Int? = null,
        commit: String? = null,
        iterationsUsed: Int? = null,
        finalCode: Map<String, String> = emptyMap(),
    ): CodeLoopStageEventModel =
        CodeLoopStageEventModel(
            stage = stage,
            iteration = iteration,
            status = status,
            files = emptyList(),
            gatewayVerdict = null,
            errors = emptyList(),
            findings = emptyList(),
            commit = commit,
            iterationsUsed = iterationsUsed,
            securityFindings = null,
            gatewayBlocks = null,
            finalCode = finalCode,
        )
}
