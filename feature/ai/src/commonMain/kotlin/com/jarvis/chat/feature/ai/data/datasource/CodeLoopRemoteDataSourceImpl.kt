package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.CodeLoopRunRequestModel
import com.jarvis.chat.feature.ai.data.model.CodeLoopStageEventResponseModel
import com.jarvis.chat.feature.ai.domain.model.CodeLoopConfigProvider
import io.ktor.client.HttpClient
import io.ktor.client.plugins.timeout
import io.ktor.client.request.preparePost
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsChannel
import io.ktor.http.ContentType
import io.ktor.http.contentType
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emitAll
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json

private const val RUN_PATH = "loop/run"
private const val STREAM_SOCKET_TIMEOUT_INFINITE_MILLIS = Long.MAX_VALUE

internal class CodeLoopRemoteDataSourceImpl(
    private val httpClient: HttpClient,
    private val codeLoopConfigProvider: CodeLoopConfigProvider,
    private val json: Json,
) : CodeLoopRemoteDataSource {

    override fun runLoop(task: String, maxIterations: Int): Flow<CodeLoopStageEventResponseModel> = flow {
        val requestBody = CodeLoopRunRequestModel(task = task, maxIterations = maxIterations)
        httpClient.preparePost(codeLoopConfigProvider.currentRootUrl() + RUN_PATH) {
            contentType(ContentType.Application.Json)
            setBody(requestBody)
            timeout { socketTimeoutMillis = STREAM_SOCKET_TIMEOUT_INFINITE_MILLIS }
        }.execute { response ->
            emitAll(codeLoopStageEventFlow(channel = response.bodyAsChannel(), json = json))
        }
    }
}
