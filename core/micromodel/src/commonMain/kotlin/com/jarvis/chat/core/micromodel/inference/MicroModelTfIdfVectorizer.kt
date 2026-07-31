package com.jarvis.chat.core.micromodel.inference

import com.jarvis.chat.core.micromodel.domain.model.MicroModelVocabularyEntryModel
import kotlin.math.sqrt

internal object MicroModelTfIdfVectorizer {

    fun vectorize(termFrequencies: Map<String, Int>, vocabulary: Map<String, MicroModelVocabularyEntryModel>): Map<Int, Double> {
        val rawValues = mutableMapOf<Int, Double>()
        for ((term, frequency) in termFrequencies) {
            val vocabularyEntry = vocabulary[term] ?: continue
            rawValues[vocabularyEntry.featureIndex] = frequency * vocabularyEntry.idf
        }
        val squaredSum = rawValues.values.sumOf { value -> value * value }
        if (squaredSum <= 0.0) {
            return rawValues
        }
        val norm = sqrt(squaredSum)
        return rawValues.mapValues { (_, value) -> value / norm }
    }
}
