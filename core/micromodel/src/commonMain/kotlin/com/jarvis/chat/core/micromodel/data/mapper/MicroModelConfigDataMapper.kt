package com.jarvis.chat.core.micromodel.data.mapper

import com.jarvis.chat.core.micromodel.data.model.MicroModelAnalyzerDataModel
import com.jarvis.chat.core.micromodel.data.model.MicroModelConfigDataModel
import com.jarvis.chat.core.micromodel.data.model.MicroModelVocabularyEntryDataModel
import com.jarvis.chat.core.micromodel.domain.model.MicroModelAnalyzerKindModel
import com.jarvis.chat.core.micromodel.domain.model.MicroModelAnalyzerModel
import com.jarvis.chat.core.micromodel.domain.model.MicroModelConfigModel
import com.jarvis.chat.core.micromodel.domain.model.MicroModelVocabularyEntryModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageRouteModel

private const val ANALYZER_KIND_WORD = "word"

internal fun MicroModelConfigDataModel.toMicroModelConfigModel(): MicroModelConfigModel =
    MicroModelConfigModel(
        labels = labels.map { label -> label.toMicroTriageRouteModel() },
        analyzers = vectorizer.analyzers.map { analyzer -> analyzer.toMicroModelAnalyzerModel() },
        vocabulary = vectorizer.vocabulary.mapValues { (_, entry) -> entry.toMicroModelVocabularyEntryModel() },
        bias = classifier.bias,
        weights = classifier.weights.entries.associate { entry -> entry.key.toInt() to entry.value },
        confidenceMinProb = thresholds.confidentMinProb,
        confidenceMinMargin = thresholds.confidentMinMargin,
        alwaysEscalateLabels = thresholds.alwaysEscalateLabels.map { label -> label.toMicroTriageRouteModel() }.toSet(),
    )

private fun String.toMicroTriageRouteModel(): MicroTriageRouteModel =
    MicroTriageRouteModel.entries.find { route -> route.name == this }
        ?: error("Unknown micro-model route label: $this")

private fun MicroModelAnalyzerDataModel.toMicroModelAnalyzerModel(): MicroModelAnalyzerModel =
    MicroModelAnalyzerModel(
        kind = if (kind == ANALYZER_KIND_WORD) MicroModelAnalyzerKindModel.WORD else MicroModelAnalyzerKindModel.CHAR,
        ngramMin = ngramMin,
        ngramMax = ngramMax,
    )

private fun MicroModelVocabularyEntryDataModel.toMicroModelVocabularyEntryModel(): MicroModelVocabularyEntryModel =
    MicroModelVocabularyEntryModel(featureIndex = i, idf = idf)
