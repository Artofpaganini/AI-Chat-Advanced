package com.jarvis.chat.feature.ai.data.datasource

import com.jarvis.chat.feature.ai.data.model.GatewayAuditEntryResponseModel
import com.jarvis.chat.feature.ai.data.model.GatewayStatsResponseModel

internal interface GatewayRemoteDataSource {

    suspend fun requestAudit(limit: Int): List<GatewayAuditEntryResponseModel>

    suspend fun requestStats(): GatewayStatsResponseModel
}
