package com.jarvis.chat.feature.ai.domain.repository

import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageEventModel
import kotlinx.coroutines.flow.Flow

interface CodeLoopRepository {

    fun runLoop(task: String, maxIterations: Int): Flow<CodeLoopStageEventModel>
}
