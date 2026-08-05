package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.feature.ai.domain.model.GatewayOutputTruncationModel
import com.jarvis.chat.feature.ai.domain.model.GatewaySignalModel
import com.jarvis.chat.feature.ai.domain.model.GatewayVerdictModel
import com.jarvis.chat.feature.chat.presentation.model.GatewaySignalUiModel
import com.jarvis.chat.feature.chat.presentation.model.GatewayVerdictUiModel
import kotlin.math.roundToLong

private const val BANNER_MASKED = "Шлюз замаскировал часть текста и отправил запрос дальше"
private const val BANNER_BLOCKED_INPUT = "Шлюз заблокировал запрос на входе"
private const val BANNER_BLOCKED_OUTPUT = "Шлюз скрыл ответ модели"
private const val BANNER_RATE_LIMITED = "Шлюз ограничил частоту запросов"
private const val BANNER_UNKNOWN = "Шлюз изменил обработку запроса"
private const val BANNER_OUTPUT_TRUNCATED = "Шлюз оборвал ответ выходным фильтром"
private const val BANNER_TRUNCATED_CHARS_PREFIX = ". Вы успели увидеть "
private const val BANNER_TRUNCATED_CHARS_SUFFIX = " знаков текста до обрыва"
private const val BANNER_REASONS_PREFIX = ". Причины: "
private const val BANNER_REASON_SEPARATOR = ", "

private const val REASON_API_KEY_OPENAI = "ключ OpenAI"
private const val REASON_API_KEY_ANTHROPIC = "ключ Anthropic"
private const val REASON_GITHUB_TOKEN = "токен GitHub"
private const val REASON_AWS_ACCESS_KEY = "ключ доступа AWS"
private const val REASON_AWS_SECRET_KEY = "секретный ключ AWS"
private const val REASON_PRIVATE_KEY_PEM = "приватный ключ"
private const val REASON_GENERIC_BEARER = "bearer-токен"
private const val REASON_CARD = "номер карты"
private const val REASON_EMAIL = "почта"
private const val REASON_PHONE = "телефон"
private const val REASON_BASE64_SECRET = "секрет в base64"
private const val REASON_SPLIT_SECRET = "разорванный на части ключ"
private const val REASON_GENERATED_SECRET = "похожий на ключ фрагмент в ответе"
private const val REASON_SYSTEM_PROMPT_LEAK = "утечка системного промпта"
private const val REASON_SUSPICIOUS_URL = "подозрительная ссылка"
private const val REASON_DANGEROUS_COMMAND = "опасная команда"
private const val REASON_PII_ECHO = "чужие персональные данные в ответе"
private const val REASON_SECRET_IN_HISTORY = "секрет найден в более раннем сообщении этого чата, не в последнем"
private const val REASON_UNKNOWN = "неизвестная причина"

private const val SHORT_REASON_API_KEY_OPENAI = "ключ OpenAI"
private const val SHORT_REASON_API_KEY_ANTHROPIC = "ключ Anthropic"
private const val SHORT_REASON_GITHUB_TOKEN = "токен GitHub"
private const val SHORT_REASON_AWS_ACCESS_KEY = "ключ AWS"
private const val SHORT_REASON_AWS_SECRET_KEY = "секрет AWS"
private const val SHORT_REASON_PRIVATE_KEY_PEM = "приватный ключ"
private const val SHORT_REASON_GENERIC_BEARER = "bearer-токен"
private const val SHORT_REASON_CARD = "карта"
private const val SHORT_REASON_EMAIL = "почта"
private const val SHORT_REASON_PHONE = "телефон"
private const val SHORT_REASON_BASE64_SECRET = "base64-секрет"
private const val SHORT_REASON_SPLIT_SECRET = "разорванный ключ"
private const val SHORT_REASON_GENERATED_SECRET = "похожий на ключ фрагмент"
private const val SHORT_REASON_SYSTEM_PROMPT_LEAK = "утечка промпта"
private const val SHORT_REASON_SUSPICIOUS_URL = "подозрительная ссылка"
private const val SHORT_REASON_DANGEROUS_COMMAND = "опасная команда"
private const val SHORT_REASON_PII_ECHO = "чужие данные"
private const val SHORT_REASON_SECRET_IN_HISTORY = "из ранней переписки"
private const val SHORT_REASON_UNKNOWN = "неизвестная причина"
private const val SHORT_REASON_SEPARATOR = ", "

private const val SHORT_MASKED_PREFIX = "Замаскировано: "
private const val SHORT_BLOCKED_INPUT = "Заблокировано на входе"
private const val SHORT_BLOCKED_INPUT_REASONS_PREFIX = "Заблокировано на входе: "
private const val SHORT_BLOCKED_OUTPUT = "Заблокировано на выходе"
private const val SHORT_BLOCKED_OUTPUT_REASONS_PREFIX = "Заблокировано на выходе: "
private const val SHORT_RATE_LIMITED = "Превышен лимит частоты"
private const val SHORT_TRUNCATED = "Ответ обрублен выходным фильтром"
private const val SHORT_TRUNCATED_REASONS_PREFIX = "Ответ обрублен выходным фильтром: "
private const val SHORT_UNKNOWN = "Шлюз изменил обработку запроса"

private const val VERDICT_LABEL_PASS = "Пройден"
private const val VERDICT_LABEL_MASKED = "Замаскирован"
private const val VERDICT_LABEL_BLOCKED_INPUT = "Заблокирован (вход)"
private const val VERDICT_LABEL_BLOCKED_OUTPUT = "Заблокирован (выход)"
private const val VERDICT_LABEL_RATE_LIMITED = "Лимит частоты"
private const val VERDICT_LABEL_UNKNOWN = "Неизвестно"

private const val COST_LABEL_PREFIX = "Шлюз: стоимость $"
private const val COST_TOKENS_SEPARATOR = " · токены "
private const val TOKENS_IN_SUFFIX = " вход"
private const val TOKENS_OUT_PREFIX = " / "
private const val TOKENS_OUT_SUFFIX = " выход"
private const val COST_DECIMAL_SCALE = 1_000_000L
private const val COST_FRACTION_DIGITS = 6

internal fun GatewaySignalModel.toGatewaySignalUiModel(
    outputTruncation: GatewayOutputTruncationModel?,
): GatewaySignalUiModel {
    val verdictUiModel = verdict.toGatewayVerdictUiModel()
    val isBannerVisible = outputTruncation != null || verdictUiModel != GatewayVerdictUiModel.PASS
    val bannerText = when {
        outputTruncation != null -> outputTruncation.toTruncationBannerText()
        verdictUiModel != GatewayVerdictUiModel.PASS -> verdictUiModel.toBannerText(reasons)
        else -> ""
    }
    val shortVerdictSummary = toGatewayShortVerdictSummary(
        outputTruncation = outputTruncation,
        verdictUiModel = verdictUiModel,
        headerReasons = reasons,
    )
    return GatewaySignalUiModel(
        isBannerVisible = isBannerVisible,
        bannerText = bannerText,
        costTokensLabel = "$COST_LABEL_PREFIX${costUsd.toGatewayCostLabel()}" +
            "$COST_TOKENS_SEPARATOR$tokensIn$TOKENS_IN_SUFFIX$TOKENS_OUT_PREFIX$tokensOut$TOKENS_OUT_SUFFIX",
        shortVerdictLabel = shortVerdictSummary.label,
        isShortVerdictWarning = shortVerdictSummary.isWarning,
    )
}

private data class GatewayShortVerdictSummary(val label: String?, val isWarning: Boolean)

private fun toGatewayShortVerdictSummary(
    outputTruncation: GatewayOutputTruncationModel?,
    verdictUiModel: GatewayVerdictUiModel,
    headerReasons: List<String>,
): GatewayShortVerdictSummary {
    if (outputTruncation != null) {
        val reasonsPart = outputTruncation.reasons.toShortReasonsPartOrNull()
        val label = if (reasonsPart != null) "$SHORT_TRUNCATED_REASONS_PREFIX$reasonsPart" else SHORT_TRUNCATED
        return GatewayShortVerdictSummary(label = label, isWarning = true)
    }
    return when (verdictUiModel) {
        GatewayVerdictUiModel.PASS -> GatewayShortVerdictSummary(label = null, isWarning = false)
        GatewayVerdictUiModel.MASKED -> {
            val reasonsPart = headerReasons.joinToString(SHORT_REASON_SEPARATOR) { reason ->
                reason.toGatewayShortReasonLabel()
            }
            GatewayShortVerdictSummary(label = "$SHORT_MASKED_PREFIX$reasonsPart", isWarning = false)
        }
        GatewayVerdictUiModel.BLOCKED_INPUT -> {
            val reasonsPart = headerReasons.toShortReasonsPartOrNull()
            val label = if (reasonsPart != null) "$SHORT_BLOCKED_INPUT_REASONS_PREFIX$reasonsPart" else SHORT_BLOCKED_INPUT
            GatewayShortVerdictSummary(label = label, isWarning = true)
        }
        GatewayVerdictUiModel.BLOCKED_OUTPUT -> {
            val reasonsPart = headerReasons.toShortReasonsPartOrNull()
            val label = if (reasonsPart != null) "$SHORT_BLOCKED_OUTPUT_REASONS_PREFIX$reasonsPart" else SHORT_BLOCKED_OUTPUT
            GatewayShortVerdictSummary(label = label, isWarning = true)
        }
        GatewayVerdictUiModel.RATE_LIMITED -> GatewayShortVerdictSummary(label = SHORT_RATE_LIMITED, isWarning = true)
        GatewayVerdictUiModel.UNKNOWN -> GatewayShortVerdictSummary(label = SHORT_UNKNOWN, isWarning = true)
    }
}

private fun List<String>.toShortReasonsPartOrNull(): String? =
    takeIf { reasons -> reasons.isNotEmpty() }
        ?.joinToString(SHORT_REASON_SEPARATOR) { reason -> reason.toGatewayShortReasonLabel() }

private fun GatewayOutputTruncationModel.toTruncationBannerText(): String {
    val reasonsPart = if (reasons.isEmpty()) {
        ""
    } else {
        val reasonLabels = reasons.map { reason -> reason.toGatewayReasonLabel() }
        "$BANNER_REASONS_PREFIX${reasonLabels.joinToString(BANNER_REASON_SEPARATOR)}"
    }
    return "$BANNER_OUTPUT_TRUNCATED$reasonsPart$BANNER_TRUNCATED_CHARS_PREFIX" +
        "$truncatedAtChars$BANNER_TRUNCATED_CHARS_SUFFIX"
}

private fun GatewayVerdictModel.toGatewayVerdictUiModel(): GatewayVerdictUiModel =
    when (this) {
        GatewayVerdictModel.PASS -> GatewayVerdictUiModel.PASS
        GatewayVerdictModel.MASKED -> GatewayVerdictUiModel.MASKED
        GatewayVerdictModel.BLOCKED_INPUT -> GatewayVerdictUiModel.BLOCKED_INPUT
        GatewayVerdictModel.BLOCKED_OUTPUT -> GatewayVerdictUiModel.BLOCKED_OUTPUT
        GatewayVerdictModel.RATE_LIMITED -> GatewayVerdictUiModel.RATE_LIMITED
        GatewayVerdictModel.UNKNOWN -> GatewayVerdictUiModel.UNKNOWN
    }

private fun GatewayVerdictUiModel.toBannerText(reasons: List<String>): String {
    val base = when (this) {
        GatewayVerdictUiModel.MASKED -> BANNER_MASKED
        GatewayVerdictUiModel.BLOCKED_INPUT -> BANNER_BLOCKED_INPUT
        GatewayVerdictUiModel.BLOCKED_OUTPUT -> BANNER_BLOCKED_OUTPUT
        GatewayVerdictUiModel.RATE_LIMITED -> BANNER_RATE_LIMITED
        GatewayVerdictUiModel.PASS, GatewayVerdictUiModel.UNKNOWN -> BANNER_UNKNOWN
    }
    if (reasons.isEmpty()) {
        return base
    }
    val reasonLabels = reasons.map { reason -> reason.toGatewayReasonLabel() }
    return "$base$BANNER_REASONS_PREFIX${reasonLabels.joinToString(BANNER_REASON_SEPARATOR)}"
}

internal fun String.toGatewayReasonLabel(): String =
    when (this) {
        "api_key_openai" -> REASON_API_KEY_OPENAI
        "api_key_anthropic" -> REASON_API_KEY_ANTHROPIC
        "github_token" -> REASON_GITHUB_TOKEN
        "aws_access_key" -> REASON_AWS_ACCESS_KEY
        "aws_secret_key" -> REASON_AWS_SECRET_KEY
        "private_key_pem" -> REASON_PRIVATE_KEY_PEM
        "generic_bearer" -> REASON_GENERIC_BEARER
        "card" -> REASON_CARD
        "email" -> REASON_EMAIL
        "phone" -> REASON_PHONE
        "base64_secret" -> REASON_BASE64_SECRET
        "split_secret" -> REASON_SPLIT_SECRET
        "generated_secret" -> REASON_GENERATED_SECRET
        "system_prompt_leak" -> REASON_SYSTEM_PROMPT_LEAK
        "suspicious_url" -> REASON_SUSPICIOUS_URL
        "dangerous_command" -> REASON_DANGEROUS_COMMAND
        "pii_echo" -> REASON_PII_ECHO
        "secret_in_history" -> REASON_SECRET_IN_HISTORY
        else -> REASON_UNKNOWN
    }

private fun String.toGatewayShortReasonLabel(): String =
    when (this) {
        "api_key_openai" -> SHORT_REASON_API_KEY_OPENAI
        "api_key_anthropic" -> SHORT_REASON_API_KEY_ANTHROPIC
        "github_token" -> SHORT_REASON_GITHUB_TOKEN
        "aws_access_key" -> SHORT_REASON_AWS_ACCESS_KEY
        "aws_secret_key" -> SHORT_REASON_AWS_SECRET_KEY
        "private_key_pem" -> SHORT_REASON_PRIVATE_KEY_PEM
        "generic_bearer" -> SHORT_REASON_GENERIC_BEARER
        "card" -> SHORT_REASON_CARD
        "email" -> SHORT_REASON_EMAIL
        "phone" -> SHORT_REASON_PHONE
        "base64_secret" -> SHORT_REASON_BASE64_SECRET
        "split_secret" -> SHORT_REASON_SPLIT_SECRET
        "generated_secret" -> SHORT_REASON_GENERATED_SECRET
        "system_prompt_leak" -> SHORT_REASON_SYSTEM_PROMPT_LEAK
        "suspicious_url" -> SHORT_REASON_SUSPICIOUS_URL
        "dangerous_command" -> SHORT_REASON_DANGEROUS_COMMAND
        "pii_echo" -> SHORT_REASON_PII_ECHO
        "secret_in_history" -> SHORT_REASON_SECRET_IN_HISTORY
        else -> SHORT_REASON_UNKNOWN
    }

internal fun GatewayVerdictModel.toShortVerdictLabel(): String =
    when (this) {
        GatewayVerdictModel.PASS -> VERDICT_LABEL_PASS
        GatewayVerdictModel.MASKED -> VERDICT_LABEL_MASKED
        GatewayVerdictModel.BLOCKED_INPUT -> VERDICT_LABEL_BLOCKED_INPUT
        GatewayVerdictModel.BLOCKED_OUTPUT -> VERDICT_LABEL_BLOCKED_OUTPUT
        GatewayVerdictModel.RATE_LIMITED -> VERDICT_LABEL_RATE_LIMITED
        GatewayVerdictModel.UNKNOWN -> VERDICT_LABEL_UNKNOWN
    }

internal fun Double.toGatewayCostLabel(): String {
    val scaled = (this * COST_DECIMAL_SCALE).roundToLong()
    val whole = scaled / COST_DECIMAL_SCALE
    val fraction = (scaled % COST_DECIMAL_SCALE).toString().padStart(COST_FRACTION_DIGITS, '0')
    return "$whole.$fraction"
}
