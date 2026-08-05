package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respondError
import io.ktor.client.plugins.ClientRequestException
import io.ktor.client.plugins.HttpRequestTimeoutException
import io.ktor.client.plugins.ServerResponseException
import io.ktor.client.request.HttpRequestBuilder
import io.ktor.client.request.get
import io.ktor.http.HttpStatusCode
import kotlinx.coroutines.test.runTest
import kotlinx.io.IOException
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

private const val HTTP_STATUS_INTERNAL_SERVER_ERROR = 500
private const val HTTP_STATUS_SERVICE_UNAVAILABLE = 503

class AiErrorMapperTest {

    @Test
    fun toAiErrorModel_onHttpRequestTimeoutException_mapsToTimeout() = runTest {
        val error = HttpRequestTimeoutException(HttpRequestBuilder())

        assertEquals(AiErrorModel.Timeout, error.toAiErrorModel())
    }

    @Test
    fun toAiErrorModel_on401ClientRequestException_mapsToUnauthorized() = runTest {
        val error = clientRequestException(status = HttpStatusCode.Unauthorized)

        assertEquals(AiErrorModel.Unauthorized, error.toAiErrorModel())
    }

    @Test
    fun toAiErrorModel_on429ClientRequestException_mapsToRateLimited() = runTest {
        val error = clientRequestException(status = HttpStatusCode.TooManyRequests)

        assertEquals(AiErrorModel.RateLimited(retryAfterSeconds = null), error.toAiErrorModel())
    }

    @Test
    fun toAiErrorModel_on400ClientRequestException_mapsToBadRequestWithApiMessage() = runTest {
        val error = clientRequestException(status = HttpStatusCode.BadRequest, content = "model overloaded")

        assertEquals(AiErrorModel.BadRequest(message = "model overloaded"), error.toAiErrorModel())
    }

    @Test
    fun toAiErrorModel_onUnmappedClientRequestException_mapsToUnknown() = runTest {
        val error = clientRequestException(status = HttpStatusCode.NotFound)

        assertEquals(AiErrorModel.Unknown, error.toAiErrorModel())
    }

    @Test
    fun toAiErrorModel_on500ServerResponseException_mapsToServerErrorWithCode() = runTest {
        val error = serverResponseException(status = HttpStatusCode.InternalServerError)

        assertEquals(AiErrorModel.ServerError(code = HTTP_STATUS_INTERNAL_SERVER_ERROR), error.toAiErrorModel())
    }

    @Test
    fun toAiErrorModel_on503ServerResponseException_mapsToServerErrorWithCode() = runTest {
        val error = serverResponseException(status = HttpStatusCode.ServiceUnavailable)

        assertEquals(AiErrorModel.ServerError(code = HTTP_STATUS_SERVICE_UNAVAILABLE), error.toAiErrorModel())
    }

    @Test
    fun toAiErrorModel_onIoException_mapsToNoConnection() = runTest {
        val error: Throwable = IOException("network down")

        assertEquals(AiErrorModel.NoConnection, error.toAiErrorModel())
    }

    @Test
    fun toAiErrorModel_onUnrelatedThrowable_mapsToUnknown() = runTest {
        val error: Throwable = IllegalStateException("boom")

        assertEquals(AiErrorModel.Unknown, error.toAiErrorModel())
    }

    private suspend fun clientRequestException(
        status: HttpStatusCode,
        content: String = "",
    ): ClientRequestException {
        val client = HttpClient(MockEngine { respondError(status = status, content = content) }) {
            expectSuccess = true
        }
        return assertFailsWith<ClientRequestException> { client.get("https://deepseek.test/error") }
    }

    private suspend fun serverResponseException(status: HttpStatusCode): ServerResponseException {
        val client = HttpClient(MockEngine { respondError(status = status) }) {
            expectSuccess = true
        }
        return assertFailsWith<ServerResponseException> { client.get("https://deepseek.test/error") }
    }
}
