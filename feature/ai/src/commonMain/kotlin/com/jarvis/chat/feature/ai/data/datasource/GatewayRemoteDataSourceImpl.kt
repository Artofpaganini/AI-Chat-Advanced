package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.GatewayAuditEntryResponseModel
import com.jarvis.chat.feature.ai.data.model.GatewayAuditListResponseModel
import com.jarvis.chat.feature.ai.data.model.GatewayStatsResponseModel
import com.jarvis.chat.feature.ai.domain.model.GatewayConfigProvider
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.parameter

private const val AUDIT_PATH = "gateway/audit"
private const val STATS_PATH = "gateway/stats"
private const val PARAM_LIMIT = "limit"

internal class GatewayRemoteDataSourceImpl(
    private val httpClient: HttpClient,
    private val gatewayConfigProvider: GatewayConfigProvider,
) : GatewayRemoteDataSource {

    override suspend fun requestAudit(limit: Int): List<GatewayAuditEntryResponseModel> {
        val response: GatewayAuditListResponseModel =
            httpClient.get(gatewayConfigProvider.currentRootUrl() + AUDIT_PATH) {
                parameter(PARAM_LIMIT, limit)
            }.body()
        return response.items
    }

    override suspend fun requestStats(): GatewayStatsResponseModel =
        httpClient.get(gatewayConfigProvider.currentRootUrl() + STATS_PATH).body()
}
