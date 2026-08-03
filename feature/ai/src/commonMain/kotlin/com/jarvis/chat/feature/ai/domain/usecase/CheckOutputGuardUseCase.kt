package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.GuardTargetModel
import com.jarvis.chat.feature.ai.domain.model.InjectionGuardSettingProvider
import com.jarvis.chat.feature.ai.domain.model.OutputGuardResultModel
import com.jarvis.chat.feature.ai.domain.repository.OutputGuardRepository

class CheckOutputGuardUseCase(
    private val repository: OutputGuardRepository,
    private val injectionGuardSettingProvider: InjectionGuardSettingProvider,
) {

    operator fun invoke(responseText: String, target: GuardTargetModel): OutputGuardResultModel =
        if (injectionGuardSettingProvider.isInjectionGuardEnabled()) {
            repository.checkOutput(responseText, target)
        } else {
            OutputGuardResultModel.Allowed
        }
}
