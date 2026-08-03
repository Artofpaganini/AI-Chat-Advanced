package com.jarvis.chat.feature.ai.domain.repository

import com.jarvis.chat.feature.ai.domain.model.GuardTargetModel
import com.jarvis.chat.feature.ai.domain.model.OutputGuardResultModel

interface OutputGuardRepository {

    fun checkOutput(responseText: String, target: GuardTargetModel): OutputGuardResultModel
}
