package com.jarvis.chat.feature.ai.data.repository

import com.jarvis.chat.feature.ai.data.datasource.CodeLoopRemoteDataSource
import com.jarvis.chat.feature.ai.data.mapper.toCodeLoopErrorModel
import com.jarvis.chat.feature.ai.data.mapper.toCodeLoopStageEventModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopConfigProvider
import com.jarvis.chat.feature.ai.domain.model.CodeLoopException
import com.jarvis.chat.feature.ai.domain.model.CodeLoopStageEventModel
import com.jarvis.chat.feature.ai.domain.repository.CodeLoopRepository
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.onEach

internal class CodeLoopRepositoryImpl(
    private val remoteDataSource: CodeLoopRemoteDataSource,
    private val codeLoopConfigProvider: CodeLoopConfigProvider,
) : CodeLoopRepository {

    override fun runLoop(task: String, maxIterations: Int): Flow<CodeLoopStageEventModel> {
        var lastEvent: CodeLoopStageEventModel? = null
        return remoteDataSource.runLoop(task = task, maxIterations = maxIterations)
            .map { response -> response.toCodeLoopStageEventModel() }
            .onEach { event -> lastEvent = event }
            .catch { throwable ->
                if (throwable is CancellationException) {
                    throw throwable
                }
                throw CodeLoopException(
                    error = throwable.toCodeLoopErrorModel(
                        rootUrl = codeLoopConfigProvider.currentRootUrl(),
                        lastEvent = lastEvent,
                    ),
                )
            }
    }
}
