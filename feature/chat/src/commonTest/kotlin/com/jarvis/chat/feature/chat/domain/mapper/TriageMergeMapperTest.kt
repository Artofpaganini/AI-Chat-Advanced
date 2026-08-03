package com.jarvis.chat.feature.chat.domain.mapper

import com.jarvis.chat.core.micromodel.domain.model.MicroTriageModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageRouteModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageStatusModel
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

private const val TEST_MARGIN = 0.1
private const val TEST_ELAPSED_MILLIS = 5L

class TriageMergeMapperTest {

    @Test
    fun toFallbackTriageModel_withLowConfidence_usesSoftenedWording() {
        val microResult = microTriageModel(confidence = 0.54)

        val triage = microResult.toFallbackTriageModel()

        assertEquals("Возможно экстренно (LLM не ответила)", triage.statusLabel)
        assertEquals(
            "Локальный классификатор заподозрил экстренную ситуацию, но не уверен, а подтверждения от большой модели нет.",
            triage.explain,
        )
        assertTrue(triage.crisis)
    }

    @Test
    fun toFallbackTriageModel_withConfidenceAtThreshold_usesCategoricalWording() {
        val microResult = microTriageModel(confidence = 0.65)

        val triage = microResult.toFallbackTriageModel()

        assertEquals("Экстренно (LLM не ответила)", triage.statusLabel)
        assertEquals(
            "Большая модель не вернула собственную оценку. Показан результат локального классификатора.",
            triage.explain,
        )
        assertTrue(triage.crisis)
    }

    @Test
    fun toFallbackTriageModel_alwaysShowsCrisisBlockRegardlessOfConfidence() {
        val lowConfidence = microTriageModel(confidence = 0.3)
        val highConfidence = microTriageModel(confidence = 0.95)

        assertTrue(lowConfidence.toFallbackTriageModel().crisis)
        assertTrue(highConfidence.toFallbackTriageModel().crisis)
    }

    private fun microTriageModel(confidence: Double): MicroTriageModel =
        MicroTriageModel(
            route = MicroTriageRouteModel.EMERGENCY,
            status = MicroTriageStatusModel.UNSURE,
            confidence = confidence,
            margin = TEST_MARGIN,
            probabilities = emptyMap(),
            elapsedMillis = TEST_ELAPSED_MILLIS,
        )
}
