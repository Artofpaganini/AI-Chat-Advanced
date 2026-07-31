package com.jarvis.chat.core.micromodel.inference

import kotlin.math.exp

internal object MicroModelSoftmaxClassifier {

    fun scoreAndSoftmax(vector: Map<Int, Double>, bias: List<Double>, weights: Map<Int, List<Double>>): DoubleArray {
        val classCount = bias.size
        val scores = DoubleArray(classCount) { classIndex -> bias[classIndex] }
        for ((featureIndex, value) in vector) {
            val featureWeights = weights[featureIndex] ?: continue
            for (classIndex in 0 until classCount) {
                scores[classIndex] += value * featureWeights[classIndex]
            }
        }
        val maxScore = scores.max()
        val exponents = DoubleArray(classCount) { classIndex -> exp(scores[classIndex] - maxScore) }
        val sumExponents = exponents.sum()
        return DoubleArray(classCount) { classIndex -> exponents[classIndex] / sumExponents }
    }
}
