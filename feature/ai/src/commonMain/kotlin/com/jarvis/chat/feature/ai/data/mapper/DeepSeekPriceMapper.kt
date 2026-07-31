package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.DeepSeekPriceModel
import com.jarvis.chat.feature.ai.di.DeepSeekDefaults
import com.jarvis.chat.feature.ai.di.MultiStageDefaults

internal fun String?.toDeepSeekPriceModelOrNull(): DeepSeekPriceModel? =
    when (this) {
        DeepSeekDefaults.CHAT_MODEL -> DeepSeekPriceModel(
            inputPricePerMillionTokens = MultiStageDefaults.PRICE_FLASH_INPUT_PER_MILLION,
            outputPricePerMillionTokens = MultiStageDefaults.PRICE_FLASH_OUTPUT_PER_MILLION,
        )
        DeepSeekDefaults.CHAT_MODEL_PRO -> DeepSeekPriceModel(
            inputPricePerMillionTokens = MultiStageDefaults.PRICE_PRO_INPUT_PER_MILLION,
            outputPricePerMillionTokens = MultiStageDefaults.PRICE_PRO_OUTPUT_PER_MILLION,
        )
        else -> null
    }

internal fun DeepSeekPriceModel.costUsdOrNull(promptTokens: Int?, completionTokens: Int?): Double? {
    if (promptTokens == null || completionTokens == null) return null
    val inputCost = promptTokens * inputPricePerMillionTokens / MultiStageDefaults.TOKENS_PER_MILLION
    val outputCost = completionTokens * outputPricePerMillionTokens / MultiStageDefaults.TOKENS_PER_MILLION
    return inputCost + outputCost
}
