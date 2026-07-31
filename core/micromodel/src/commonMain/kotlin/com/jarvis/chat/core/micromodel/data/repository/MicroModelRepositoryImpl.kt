package com.jarvis.chat.core.micromodel.data.repository

import com.jarvis.chat.core.micromodel.data.datasource.MicroModelConfigLocalDataSource
import com.jarvis.chat.core.micromodel.data.mapper.toMicroModelConfigModel
import com.jarvis.chat.core.micromodel.domain.model.MicroModelConfigModel
import com.jarvis.chat.core.micromodel.domain.model.MicroTriageModel
import com.jarvis.chat.core.micromodel.domain.repository.MicroModelRepository
import com.jarvis.chat.core.micromodel.inference.MicroModelFeatureExtractor
import com.jarvis.chat.core.micromodel.inference.MicroModelSoftmaxClassifier
import com.jarvis.chat.core.micromodel.inference.MicroModelTextNormalizer
import com.jarvis.chat.core.micromodel.inference.MicroModelTfIdfVectorizer
import com.jarvis.chat.core.micromodel.inference.MicroModelTriageDecision
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlin.time.TimeSource

private const val MAX_CLASSIFICATION_TEXT_LENGTH = 4_000

internal class MicroModelRepositoryImpl(
    private val configLocalDataSource: MicroModelConfigLocalDataSource,
) : MicroModelRepository {

    private val configMutex = Mutex()
    private var cachedConfig: MicroModelConfigModel? = null

    override suspend fun classify(text: String): MicroTriageModel? = withContext(Dispatchers.Default) {
        val config = loadConfig() ?: return@withContext null
        val startMark = TimeSource.Monotonic.markNow()
        val truncatedText = text.take(MAX_CLASSIFICATION_TEXT_LENGTH)
        val normalizedText = MicroModelTextNormalizer.normalize(truncatedText)
        val termFrequencies = MicroModelFeatureExtractor.extractTermFrequencies(
            normalizedText = normalizedText,
            analyzers = config.analyzers,
        )
        val vector = MicroModelTfIdfVectorizer.vectorize(
            termFrequencies = termFrequencies,
            vocabulary = config.vocabulary,
        )
        val probabilities = MicroModelSoftmaxClassifier.scoreAndSoftmax(
            vector = vector,
            bias = config.bias,
            weights = config.weights,
        )
        val elapsedMillis = startMark.elapsedNow().inWholeMilliseconds
        MicroModelTriageDecision.decide(
            probabilities = probabilities,
            config = config,
            elapsedMillis = elapsedMillis,
        )
    }

    @Suppress("TooGenericExceptionCaught", "SwallowedException")
    private suspend fun loadConfig(): MicroModelConfigModel? = configMutex.withLock {
        cachedConfig?.let { config -> return@withLock config }
        try {
            configLocalDataSource.load().toMicroModelConfigModel().also { config -> cachedConfig = config }
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (exception: Exception) {
            null
        }
    }
}
