package com.jarvis.chat.feature.ai.data.repository

import com.jarvis.chat.feature.ai.data.mapper.checkOutputGuard
import com.jarvis.chat.feature.ai.domain.model.GuardTargetModel
import com.jarvis.chat.feature.ai.domain.model.OutputGuardResultModel
import com.jarvis.chat.feature.ai.domain.repository.OutputGuardRepository

internal class OutputGuardRepositoryImpl : OutputGuardRepository {

    override fun checkOutput(responseText: String, target: GuardTargetModel): OutputGuardResultModel =
        checkOutputGuard(responseText, target)
}
