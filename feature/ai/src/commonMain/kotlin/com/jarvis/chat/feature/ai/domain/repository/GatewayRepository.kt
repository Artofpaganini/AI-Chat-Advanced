package com.jarvis.chat.feature.ai.domain.repository

import com.jarvis.chat.feature.ai.domain.model.GatewayAuditEntryModel
import com.jarvis.chat.feature.ai.domain.model.GatewayStatsModel

interface GatewayRepository {

    suspend fun loadAudit(limit: Int): List<GatewayAuditEntryModel>

    suspend fun loadStats(): GatewayStatsModel
}
