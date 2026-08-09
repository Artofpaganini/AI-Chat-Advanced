package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.CodeLoopFindingResponseModel
import com.jarvis.chat.feature.ai.data.model.CodeLoopStageEventResponseModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopSeverityModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStatusModel
import com.jarvis.chat.feature.ai.domain.model.GatewayVerdictModel
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class CodeLoopEventMapperTest {

    @Test
    fun toCodeLoopStageEventModel_onGenerateDoneEvent_mapsAllFields() {
        val response = CodeLoopStageEventResponseModel(
            stage = "GENERATE",
            iteration = 1,
            status = "done",
            files = listOf("TokenStorage.kt"),
            gatewayVerdict = "pass",
        )

        val model = response.toCodeLoopStageEventModel()

        assertEquals(CodeLoopStageModel.GENERATE, model.stage)
        assertEquals(CodeLoopStatusModel.DONE, model.status)
        assertEquals(listOf("TokenStorage.kt"), model.files)
        assertEquals(GatewayVerdictModel.PASS, model.gatewayVerdict)
    }

    @Test
    fun toCodeLoopStageEventModel_onUnknownStageAndStatus_fallsBackToUnknown() {
        val response = CodeLoopStageEventResponseModel(stage = "UNEXPECTED", status = "weird")

        val model = response.toCodeLoopStageEventModel()

        assertEquals(CodeLoopStageModel.UNKNOWN, model.stage)
        assertEquals(CodeLoopStatusModel.UNKNOWN, model.status)
    }

    @Test
    fun toCodeLoopStageEventModel_onSecurityFinding_mapsSeverityAndFields() {
        val response = CodeLoopStageEventResponseModel(
            stage = "SECURITY",
            iteration = 2,
            status = "failed",
            findings = listOf(
                CodeLoopFindingResponseModel(
                    severity = "HIGH",
                    file = "TokenStorage.kt",
                    line = 14,
                    title = "токен в обычных настройках",
                    fix = "перейти на EncryptedSharedPreferences",
                ),
            ),
        )

        val model = response.toCodeLoopStageEventModel()

        val finding = model.findings.single()
        assertEquals(CodeLoopSeverityModel.HIGH, finding.severity)
        assertEquals("TokenStorage.kt", finding.file)
        assertEquals(14, finding.line)
    }

    @Test
    fun toCodeLoopStageEventModel_onMissingOptionalFields_defaultsToEmpty() {
        val response = CodeLoopStageEventResponseModel(stage = "LINT", status = "failed")

        val model = response.toCodeLoopStageEventModel()

        assertEquals(emptyList(), model.errors)
        assertEquals(emptyList(), model.findings)
        assertEquals(emptyMap(), model.finalCode)
        assertNull(model.gatewayVerdict)
    }

    @Test
    fun toCodeLoopStageEventModel_onResultWithFinalCode_mapsFileContentMap() {
        val response = CodeLoopStageEventResponseModel(
            stage = "RESULT",
            status = "done",
            iterationsUsed = 3,
            finalCode = mapOf("TokenStorage.kt" to "class TokenStorage"),
        )

        val model = response.toCodeLoopStageEventModel()

        assertEquals(mapOf("TokenStorage.kt" to "class TokenStorage"), model.finalCode)
    }
}
