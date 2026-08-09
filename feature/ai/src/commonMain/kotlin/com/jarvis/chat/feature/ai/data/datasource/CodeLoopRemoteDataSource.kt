package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.CodeLoopStageEventResponseModel
import kotlinx.coroutines.flow.Flow

internal interface CodeLoopRemoteDataSource {

    fun runLoop(task: String, maxIterations: Int): Flow<CodeLoopStageEventResponseModel>
}
