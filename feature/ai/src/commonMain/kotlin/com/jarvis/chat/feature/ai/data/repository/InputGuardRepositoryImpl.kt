package com.jarvis.chat.feature.ai.data.repository

import com.jarvis.chat.feature.ai.data.mapper.checkInputGuard
import com.jarvis.chat.feature.ai.domain.model.InputGuardResultModel
import com.jarvis.chat.feature.ai.domain.repository.InputGuardRepository

internal class InputGuardRepositoryImpl : InputGuardRepository {

    override fun checkInput(rawText: String): InputGuardResultModel = checkInputGuard(rawText)
}
