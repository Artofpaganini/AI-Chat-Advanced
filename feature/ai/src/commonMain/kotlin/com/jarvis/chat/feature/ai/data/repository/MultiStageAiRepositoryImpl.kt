package com.jarvis.chat.feature.ai.data.repository

import com.jarvis.chat.feature.ai.data.datasource.DeepSeekRemoteDataSource
import com.jarvis.chat.feature.ai.data.mapper.costUsdOrNull
import com.jarvis.chat.feature.ai.data.mapper.emptyMultiStageFacts
import com.jarvis.chat.feature.ai.data.mapper.parseStage1Facts
import com.jarvis.chat.feature.ai.data.mapper.parseStage2Decision
import com.jarvis.chat.feature.ai.data.mapper.toDeepSeekPriceModelOrNull
import com.jarvis.chat.feature.ai.data.mapper.toFormattedFacts
import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.data.model.ChatMessageRequestModel
import com.jarvis.chat.feature.ai.di.MultiStageDefaults
import com.jarvis.chat.feature.ai.domain.model.MultiStageAnswerStepModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageDecideStepModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageParseStepModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageResultModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageStageModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageStepMetaModel
import com.jarvis.chat.feature.ai.domain.model.MultiStageViolationModel
import com.jarvis.chat.feature.ai.domain.repository.MultiStageAiRepository
import kotlinx.coroutines.CancellationException
import kotlin.time.TimeSource

private const val ROLE_SYSTEM = "system"
private const val ROLE_USER = "user"
private const val MONOLITHIC_CALL_COUNT_PARSE_AND_DECIDE = 2
private const val MULTI_STAGE_CALL_COUNT_ALL = 3

private data class RawStageCallResult(
    val text: String,
    val latencyMs: Long,
    val promptTokens: Int?,
    val completionTokens: Int?,
    val costUsd: Double?,
    val errorText: String?,
)

internal class MultiStageAiRepositoryImpl(
    private val remoteDataSource: DeepSeekRemoteDataSource,
) : MultiStageAiRepository {

    override suspend fun runMultiStage(caseText: String): MultiStageResultModel {
        val startMark = TimeSource.Monotonic.markNow()

        val parseCall = callStage(
            systemPrompt = MultiStageDefaults.STAGE1_SYSTEM_PROMPT,
            userContent = MultiStageDefaults.stage1UserContent(caseText),
            maxTokens = MultiStageDefaults.STAGE1_MAX_TOKENS,
        )
        val parseOutcome = parseStage1Facts(parseCall.text)
        val parseOk = parseCall.errorText == null &&
            MultiStageViolationModel.S1_PARSE !in parseOutcome.violations
        val parseStep = MultiStageParseStepModel(
            facts = parseOutcome.facts,
            meta = parseCall.toMeta(violations = parseOutcome.violations, isOk = parseOk),
        )
        val factsForDecision = if (parseOk) parseOutcome.facts else emptyMultiStageFacts()
        var failedStage: MultiStageStageModel? = if (!parseOk) MultiStageStageModel.PARSE else null

        val decideCall = callStage(
            systemPrompt = MultiStageDefaults.STAGE2_SYSTEM_PROMPT,
            userContent = MultiStageDefaults.stage2UserContent(factsForDecision.toFormattedFacts()),
            maxTokens = MultiStageDefaults.STAGE2_MAX_TOKENS,
        )
        val decideOutcome = parseStage2Decision(decideCall.text)
        val decideOk = decideCall.errorText == null && decideOutcome.decision.route != null
        val decideStep = MultiStageDecideStepModel(
            decision = decideOutcome.decision,
            meta = decideCall.toMeta(violations = decideOutcome.violations, isOk = decideOk),
        )
        if (!decideOk && failedStage == null) {
            failedStage = MultiStageStageModel.DECIDE
        }

        if (!decideOk) {
            return MultiStageResultModel(
                parseStep = parseStep,
                decideStep = decideStep,
                answerStep = null,
                route = null,
                answerText = MultiStageDefaults.FALLBACK_ANSWER,
                failedStage = failedStage,
                totalLatencyMs = startMark.elapsedNow().inWholeMilliseconds,
                totalCalls = MONOLITHIC_CALL_COUNT_PARSE_AND_DECIDE,
                totalCostUsd = sumCostOrNull(parseStep.meta.costUsd, decideStep.meta.costUsd),
            )
        }

        val route = requireNotNull(decideOutcome.decision.route)
        val answerCall = callStage(
            systemPrompt = MultiStageDefaults.STAGE3_SYSTEM_PROMPT,
            userContent = MultiStageDefaults.stage3UserContent(
                route = route.name,
                why = decideOutcome.decision.why.ifBlank { MultiStageDefaults.NONE_VALUE },
                facts = factsForDecision.toFormattedFacts(),
            ),
            maxTokens = MultiStageDefaults.STAGE3_MAX_TOKENS,
        )
        val trimmedAnswer = answerCall.text.trim()
        val answerOk = answerCall.errorText == null && trimmedAnswer.length >= MultiStageDefaults.MIN_ANSWER_CHARS
        val answerViolations = if (answerOk) emptyList() else listOf(MultiStageViolationModel.S3_EMPTY)
        val answerText = if (answerOk) {
            trimmedAnswer.take(MultiStageDefaults.MAX_ANSWER_CHARS)
        } else {
            MultiStageDefaults.FALLBACK_ANSWER
        }
        val answerStep = MultiStageAnswerStepModel(
            answerText = answerText,
            meta = answerCall.toMeta(violations = answerViolations, isOk = answerOk),
        )
        if (!answerOk && failedStage == null) {
            failedStage = MultiStageStageModel.ANSWER
        }

        return MultiStageResultModel(
            parseStep = parseStep,
            decideStep = decideStep,
            answerStep = answerStep,
            route = route,
            answerText = answerText,
            failedStage = failedStage,
            totalLatencyMs = startMark.elapsedNow().inWholeMilliseconds,
            totalCalls = MULTI_STAGE_CALL_COUNT_ALL,
            totalCostUsd = sumCostOrNull(parseStep.meta.costUsd, decideStep.meta.costUsd, answerStep.meta.costUsd),
        )
    }

    @Suppress("TooGenericExceptionCaught")
    private suspend fun callStage(
        systemPrompt: String,
        userContent: String,
        maxTokens: Int,
    ): RawStageCallResult {
        val messages = listOf(
            ChatMessageRequestModel(role = ROLE_SYSTEM, content = systemPrompt),
            ChatMessageRequestModel(role = ROLE_USER, content = userContent),
        )
        val mark = TimeSource.Monotonic.markNow()
        return try {
            val response = remoteDataSource.requestRawCompletion(messages = messages, maxTokens = maxTokens)
            response.toRawStageCallResult(latencyMs = mark.elapsedNow().inWholeMilliseconds)
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (throwable: Throwable) {
            RawStageCallResult(
                text = "",
                latencyMs = mark.elapsedNow().inWholeMilliseconds,
                promptTokens = null,
                completionTokens = null,
                costUsd = null,
                errorText = throwable.message ?: throwable::class.simpleName.orEmpty(),
            )
        }
    }

    private fun ChatCompletionResponseModel.toRawStageCallResult(latencyMs: Long): RawStageCallResult {
        val text = choices.firstOrNull()?.message?.content.orEmpty().trim()
        val promptTokens = usage?.promptTokens
        val completionTokens = usage?.completionTokens
        val cost = model.toDeepSeekPriceModelOrNull()?.costUsdOrNull(promptTokens, completionTokens)
        return RawStageCallResult(
            text = text,
            latencyMs = latencyMs,
            promptTokens = promptTokens,
            completionTokens = completionTokens,
            costUsd = cost,
            errorText = null,
        )
    }

    private fun RawStageCallResult.toMeta(
        violations: List<MultiStageViolationModel>,
        isOk: Boolean,
    ): MultiStageStepMetaModel = MultiStageStepMetaModel(
        rawText = text,
        latencyMs = latencyMs,
        promptTokens = promptTokens,
        completionTokens = completionTokens,
        costUsd = costUsd,
        violations = violations,
        isOk = isOk,
        errorText = errorText,
    )

    private fun sumCostOrNull(vararg costs: Double?): Double? {
        val known = costs.filterNotNull()
        return if (known.isEmpty()) null else known.sum()
    }
}
