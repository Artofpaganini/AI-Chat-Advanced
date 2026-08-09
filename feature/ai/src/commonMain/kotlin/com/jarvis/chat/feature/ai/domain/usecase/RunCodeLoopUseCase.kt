package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageEventModel
import com.jarvis.chat.feature.ai.domain.repository.CodeLoopRepository
import kotlinx.coroutines.flow.Flow

class RunCodeLoopUseCase(
    private val repository: CodeLoopRepository,
) {

    operator fun invoke(task: String, maxIterations: Int): Flow<CodeLoopStageEventModel> =
        repository.runLoop(task = task, maxIterations = maxIterations)
}
