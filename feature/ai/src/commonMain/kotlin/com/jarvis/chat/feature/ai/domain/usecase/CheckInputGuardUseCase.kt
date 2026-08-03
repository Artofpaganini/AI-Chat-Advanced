package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.InjectionGuardSettingProvider
import com.jarvis.chat.feature.ai.domain.model.InputGuardResultModel
import com.jarvis.chat.feature.ai.domain.repository.InputGuardRepository

class CheckInputGuardUseCase(
    private val repository: InputGuardRepository,
    private val injectionGuardSettingProvider: InjectionGuardSettingProvider,
) {

    operator fun invoke(rawText: String): InputGuardResultModel =
        if (injectionGuardSettingProvider.isInjectionGuardEnabled()) {
            repository.checkInput(rawText)
        } else {
            InputGuardResultModel.Allowed
        }
}
