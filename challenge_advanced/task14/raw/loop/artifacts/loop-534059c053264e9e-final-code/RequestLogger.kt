package com.jarvis.chat.feature.loopgenerated

import android.util.Log
import io.ktor.client.HttpClient
import io.ktor.client.plugins.HttpReceive
import io.ktor.client.plugins.HttpSend

internal object RequestLogger {
    private const val TAG = "HttpClient"

    fun install(client: HttpClient) {
        client.plugin(HttpSend).intercept { request ->
            Log.d(TAG, "SEND ${request.method.value} ${request.url}")
            execute(request)
        }

        client.plugin(HttpReceive).intercept { response ->
            val request = response.request
            Log.d(TAG, "RECEIVE ${response.status.value} ${request.method.value} ${request.url}")
            response
        }
    }
}

internal fun HttpClient.withRequestLogging(): HttpClient {
    RequestLogger.install(this)
    return this
}
