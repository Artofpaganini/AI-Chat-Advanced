package com.jarvis.chat.core.micromodel.inference

import com.jarvis.chat.core.micromodel.domain.model.MicroModelConfigModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageStatusModel

internal object MicroModelTriageDecision {

    fun decide(probabilities: DoubleArray, config: MicroModelConfigModel, elapsedMillis: Long): MicroTriageModel {
        val sortedIndices = probabilities.indices.sortedByDescending { index -> probabilities[index] }
        val topIndex = sortedIndices[0]
        val secondIndex = sortedIndices.getOrNull(1)
        val topProbability = probabilities[topIndex]
        val secondProbability = secondIndex?.let { index -> probabilities[index] } ?: 0.0
        val margin = topProbability - secondProbability
        val route = config.labels[topIndex]
        val isConfident = topProbability >= config.confidenceMinProb && margin >= config.confidenceMinMargin
        val isForcedUnsure = route in config.alwaysEscalateLabels
        val status = if (isConfident && !isForcedUnsure) MicroTriageStatusModel.OK else MicroTriageStatusModel.UNSURE
        return MicroTriageModel(
            route = route,
            status = status,
            confidence = topProbability,
            margin = margin,
            probabilities = config.labels.indices.associate { index -> config.labels[index] to probabilities[index] },
            elapsedMillis = elapsedMillis,
        )
    }
}
