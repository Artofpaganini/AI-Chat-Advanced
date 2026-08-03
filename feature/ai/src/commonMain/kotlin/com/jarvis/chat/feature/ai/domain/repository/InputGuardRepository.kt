package com.jarvis.chat.feature.ai.domain.repository

import com.jarvis.chat.feature.ai.domain.model.InputGuardResultModel

interface InputGuardRepository {

    fun checkInput(rawText: String): InputGuardResultModel
}
