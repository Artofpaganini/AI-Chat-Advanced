package com.jarvis.chat.core.micromodel.domain.usecase

import com.jarvis.chat.core.micromodel.data.datasource.MicroModelConfigLocalDataSource
import com.jarvis.chat.core.micromodel.data.model.MicroModelConfigDataModel
import com.jarvis.chat.core.micromodel.data.repository.MicroModelRepositoryImpl
import kotlinx.coroutines.test.runTest
import kotlinx.io.buffered
import kotlinx.io.files.Path
import kotlinx.io.files.SystemFileSystem
import kotlinx.io.readString
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

private const val CASES_PATH = "challenge_advanced/task7/data/cases.jsonl"
private const val PARITY_PATH = "challenge_advanced/task10/results/parity_python.json"
private const val MICRO_MODEL_JSON_PATH = "core/micromodel/src/commonMain/composeResources/files/micro_model.json"
private const val PROBABILITY_TOLERANCE = 1e-6

private class FileBasedMicroModelConfigLocalDataSource(private val json: Json) : MicroModelConfigLocalDataSource {

    override suspend fun load(): MicroModelConfigDataModel {
        val content = SystemFileSystem.source(Path(MICRO_MODEL_JSON_PATH)).buffered().use { source -> source.readString() }
        return json.decodeFromString(content)
    }
}

@Serializable
private data class ParityFileJson(
    val labels: List<String>,
    val entries: List<ParityCaseJson>,
)

@Serializable
private data class ParityCaseJson(
    val id: String,
    val label: String,
    val prob: Double,
    val margin: Double,
    val status: String,
    val probs: List<Double>,
)

@Serializable
private data class TriageCaseJson(
    val id: String,
    val text: String,
)

class MicroModelParityTest {

    @Test
    fun classifyMessageUseCase_matchesPythonParity_forEveryCase() = runTest {
        val parityPath = Path(PARITY_PATH)
        assertTrue(
            SystemFileSystem.exists(parityPath),
            "Эталон паритета не найден: $PARITY_PATH. Паритет-тест обязан падать, а не пропускаться " +
                "(WEIGHTS_FORMAT.md, раздел 6) - сгенерируйте parity_python.json Python-харнессом.",
        )

        val json = Json { ignoreUnknownKeys = true }
        val parityFile = json.decodeFromString<ParityFileJson>(parityPath.readText())
        assertTrue(parityFile.entries.isNotEmpty(), "parity_python.json пуст")

        val casesById = Path(CASES_PATH).readText()
            .lineSequence()
            .filter { line -> line.isNotBlank() }
            .map { line -> json.decodeFromString<TriageCaseJson>(line) }
            .associateBy { case -> case.id }

        val useCase = ClassifyMessageUseCase(
            repository = MicroModelRepositoryImpl(
                configLocalDataSource = FileBasedMicroModelConfigLocalDataSource(json = json),
            ),
        )

        for (parityCase in parityFile.entries) {
            val case = casesById.getValue(parityCase.id)
            val result = useCase(case.text)
            assertNotNull(result, "Kotlin-классификатор вернул null для кейса ${parityCase.id}")
            assertEquals(parityCase.label, result.route.name, "route разошёлся на кейсе ${parityCase.id}")
            assertEquals(parityCase.status, result.status.name, "status разошёлся на кейсе ${parityCase.id}")
            assertProbabilityClose(parityCase.prob, result.confidence, "prob", parityCase.id)
            assertProbabilityClose(parityCase.margin, result.margin, "margin", parityCase.id)
            for (labelIndex in parityFile.labels.indices) {
                val labelName = parityFile.labels[labelIndex]
                val expectedProbability = parityCase.probs[labelIndex]
                val actualProbability = result.probabilities.entries.find { entry -> entry.key.name == labelName }?.value
                assertNotNull(actualProbability, "В Kotlin-векторе нет вероятности для класса $labelName (кейс ${parityCase.id})")
                assertProbabilityClose(expectedProbability, actualProbability, "probs[$labelName]", parityCase.id)
            }
        }
    }

    private fun assertProbabilityClose(expected: Double, actual: Double, field: String, caseId: String) {
        val difference = kotlin.math.abs(expected - actual)
        assertTrue(
            difference <= PROBABILITY_TOLERANCE,
            "$field разошёлся на кейсе $caseId: python=$expected kotlin=$actual diff=$difference",
        )
    }

    private fun Path.readText(): String = SystemFileSystem.source(this).buffered().use { source -> source.readString() }
}
