package com.jarvis.chat.di

import com.jarvis.chat.AppConfig
import com.jarvis.chat.feature.ai.di.DeepSeekDefaults
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigModel
import com.jarvis.chat.feature.ai.domain.model.AiProviderConfigProvider
import com.jarvis.chat.feature.ai.domain.model.AiProviderTypeModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekConfigModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekModelIdModel
import com.jarvis.chat.feature.ai.domain.model.DeepSeekModelProvider
import com.jarvis.chat.feature.ai.domain.model.InferenceModeModel as AiInferenceModeModel
import com.jarvis.chat.feature.ai.domain.model.InferenceModeProvider
import com.jarvis.chat.feature.chat.di.chatModule
import com.jarvis.chat.feature.chat.domain.model.MicroModelGateSettingProvider
import com.jarvis.chat.feature.settings.di.settingsModule
import com.jarvis.chat.feature.settings.domain.model.AiModelModel
import com.jarvis.chat.feature.settings.domain.model.AiProviderModel
import com.jarvis.chat.feature.settings.domain.model.InferenceModeModel
import com.jarvis.chat.feature.settings.domain.usecase.ObserveAiModelUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveAiProviderUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveInferenceModeUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveMicroModelFirstEnabledUseCase
import org.koin.core.context.startKoin
import org.koin.dsl.module
import org.koin.mp.KoinPlatform

fun initKoin(appConfig: AppConfig) {
    if (KoinPlatform.getKoinOrNull() != null) {
        return
    }
    startKoin {
        modules(
            module {
                single { appConfig }
                single { DeepSeekConfigModel(apiKey = appConfig.deepSeekApiKey) }
                single<AiProviderConfigProvider> {
                    val observeAiModelUseCase: ObserveAiModelUseCase = get()
                    val observeAiProviderUseCase: ObserveAiProviderUseCase = get()
                    AiProviderConfigProvider {
                        when (observeAiProviderUseCase().value.toAiProviderType()) {
                            AiProviderTypeModel.CLOUD_DEEP_SEEK -> AiProviderConfigModel(
                                baseUrl = appConfig.deepSeekBaseUrl,
                                modelId = observeAiModelUseCase().value.toDeepSeekModelId(),
                                systemPrompt = DeepSeekDefaults.SYSTEM_PROMPT,
                                isApiKeyRequired = true,
                                adapterPath = null,
                                maxTokens = null,
                                temperature = null,
                                repetitionPenalty = null,
                            )
                            AiProviderTypeModel.LOCAL_MLX -> AiProviderConfigModel(
                                baseUrl = appConfig.localModelBaseUrl,
                                modelId = DeepSeekDefaults.LOCAL_MODEL_ID,
                                systemPrompt = DeepSeekDefaults.LOCAL_SYSTEM_PROMPT,
                                isApiKeyRequired = false,
                                adapterPath = appConfig.localModelAdapterPath,
                                maxTokens = DeepSeekDefaults.LOCAL_MAX_TOKENS,
                                temperature = DeepSeekDefaults.LOCAL_TEMPERATURE,
                                repetitionPenalty = DeepSeekDefaults.LOCAL_REPETITION_PENALTY,
                            )
                            AiProviderTypeModel.LOCAL_TRIAGE -> AiProviderConfigModel(
                                baseUrl = appConfig.triageBaseUrl,
                                modelId = DeepSeekDefaults.TRIAGE_MODEL_ID,
                                systemPrompt = DeepSeekDefaults.LOCAL_SYSTEM_PROMPT,
                                isApiKeyRequired = false,
                                adapterPath = null,
                                maxTokens = null,
                                temperature = null,
                                repetitionPenalty = null,
                            )
                        }
                    }
                }
                single<DeepSeekModelProvider> {
                    val providerConfigProvider: AiProviderConfigProvider = get()
                    DeepSeekModelProvider { providerConfigProvider.currentConfig().modelId }
                }
                single<MicroModelGateSettingProvider> {
                    val observeMicroModelFirstEnabledUseCase: ObserveMicroModelFirstEnabledUseCase = get()
                    MicroModelGateSettingProvider { observeMicroModelFirstEnabledUseCase().value }
                }
                single<InferenceModeProvider> {
                    val observeInferenceModeUseCase: ObserveInferenceModeUseCase = get()
                    InferenceModeProvider { observeInferenceModeUseCase().value.toAiInferenceModeModel() }
                }
            },
            chatModule(storageDirectoryPath = appConfig.filesDirectoryPath),
            settingsModule,
        )
    }
}

private fun AiModelModel.toDeepSeekModelId(): String =
    when (this) {
        AiModelModel.FLASH -> DeepSeekModelIdModel.FLASH.apiId
        AiModelModel.PRO -> DeepSeekModelIdModel.PRO.apiId
    }

private fun AiProviderModel.toAiProviderType(): AiProviderTypeModel =
    when (this) {
        AiProviderModel.DEEP_SEEK_CLOUD -> AiProviderTypeModel.CLOUD_DEEP_SEEK
        AiProviderModel.LOCAL_MLX -> AiProviderTypeModel.LOCAL_MLX
        AiProviderModel.LOCAL_TRIAGE -> AiProviderTypeModel.LOCAL_TRIAGE
    }

private fun InferenceModeModel.toAiInferenceModeModel(): AiInferenceModeModel =
    when (this) {
        InferenceModeModel.ONE_SHOT -> AiInferenceModeModel.ONE_SHOT
        InferenceModeModel.MULTI_STAGE -> AiInferenceModeModel.MULTI_STAGE
    }
