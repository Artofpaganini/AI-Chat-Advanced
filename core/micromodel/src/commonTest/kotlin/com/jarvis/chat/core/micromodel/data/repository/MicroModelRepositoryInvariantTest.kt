package com.jarvis.chat.core.micromodel.data.repository

import com.jarvis.chat.core.micromodel.data.datasource.MicroModelConfigLocalDataSource
import com.jarvis.chat.core.micromodel.data.model.MicroModelAnalyzerDataModel
import com.jarvis.chat.core.micromodel.data.model.MicroModelClassifierDataModel
import com.jarvis.chat.core.micromodel.data.model.MicroModelConfigDataModel
import com.jarvis.chat.core.micromodel.data.model.MicroModelNormalizerDataModel
import com.jarvis.chat.core.micromodel.data.model.MicroModelThresholdsDataModel
import com.jarvis.chat.core.micromodel.data.model.MicroModelVectorizerDataModel
import com.jarvis.chat.core.micromodel.data.model.MicroModelVocabularyEntryDataModel
import com.jarvis.chat.core.micromodel.domain.usecase.ClassifyMessageUseCase
import kotlinx.coroutines.test.runTest
import kotlin.test.Test
import kotlin.test.assertNull

private const val ANALYZER_KIND_WORD = "word"

private class BrokenMicroModelConfigLocalDataSource : MicroModelConfigLocalDataSource {

    override suspend fun load(): MicroModelConfigDataModel =
        MicroModelConfigDataModel(
            formatVersion = 1,
            labels = listOf("EMERGENCY", "DOCTOR_SOON", "SELF_CARE", "OFF_TOPIC"),
            normalizer = MicroModelNormalizerDataModel(),
            vectorizer = MicroModelVectorizerDataModel(
                kind = "tfidf",
                norm = "l2",
                analyzers = listOf(MicroModelAnalyzerDataModel(kind = ANALYZER_KIND_WORD, ngramMin = 1, ngramMax = 1)),
                vocabulary = mapOf("w:тест" to MicroModelVocabularyEntryDataModel(i = 0, idf = 1.0)),
            ),
            classifier = MicroModelClassifierDataModel(
                kind = "logreg_softmax",
                bias = listOf(0.0, 0.0, 0.0, 0.0),
                weights = mapOf("0" to listOf(0.0, 0.0, 0.0, 0.0)),
            ),
            thresholds = MicroModelThresholdsDataModel(
                confidentMinProb = 0.5,
                confidentMinMargin = 0.1,
                alwaysEscalateLabels = emptyList(),
            ),
        )
}

class MicroModelRepositoryInvariantTest {

    @Test
    fun classify_returnsNull_whenAlwaysEscalateLabelsMissesEmergency() = runTest {
        val useCase = ClassifyMessageUseCase(
            repository = MicroModelRepositoryImpl(configLocalDataSource = BrokenMicroModelConfigLocalDataSource()),
        )

        val result = useCase("любой текст пользователя")

        assertNull(result, "Веса без EMERGENCY в always_escalate_labels обязаны быть отвергнуты целиком")
    }
}
