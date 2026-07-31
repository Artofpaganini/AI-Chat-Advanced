package com.jarvis.chat.core.micromodel.inference

import com.jarvis.chat.core.micromodel.domain.model.MicroModelAnalyzerKindModel
import com.jarvis.chat.core.micromodel.domain.model.MicroModelAnalyzerModel

private const val WORD_PREFIX = "w:"
private const val CHAR_PREFIX = "c:"
private const val WORD_SEPARATOR = " "

internal object MicroModelFeatureExtractor {

    fun extractTermFrequencies(normalizedText: String, analyzers: List<MicroModelAnalyzerModel>): Map<String, Int> {
        val termCounts = mutableMapOf<String, Int>()
        val words = normalizedText.split(WORD_SEPARATOR).filter { word -> word.isNotEmpty() }
        for (analyzer in analyzers) {
            when (analyzer.kind) {
                MicroModelAnalyzerKindModel.WORD -> extractWordNgrams(words, analyzer, termCounts)
                MicroModelAnalyzerKindModel.CHAR -> extractCharNgrams(normalizedText, analyzer, termCounts)
            }
        }
        return termCounts
    }

    private fun extractWordNgrams(words: List<String>, analyzer: MicroModelAnalyzerModel, termCounts: MutableMap<String, Int>) {
        for (ngramSize in analyzer.ngramMin..analyzer.ngramMax) {
            if (ngramSize <= 0 || ngramSize > words.size) {
                continue
            }
            for (start in 0..words.size - ngramSize) {
                val ngram = words.subList(start, start + ngramSize).joinToString(separator = WORD_SEPARATOR)
                termCounts.increment(term = "$WORD_PREFIX$ngram")
            }
        }
    }

    private fun extractCharNgrams(text: String, analyzer: MicroModelAnalyzerModel, termCounts: MutableMap<String, Int>) {
        for (windowSize in analyzer.ngramMin..analyzer.ngramMax) {
            if (windowSize <= 0 || windowSize > text.length) {
                continue
            }
            for (start in 0..text.length - windowSize) {
                val ngram = text.substring(start, start + windowSize)
                termCounts.increment(term = "$CHAR_PREFIX$ngram")
            }
        }
    }

    private fun MutableMap<String, Int>.increment(term: String) {
        this[term] = (this[term] ?: 0) + 1
    }
}
