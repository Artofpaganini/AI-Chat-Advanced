package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.GatewayAuditEntryModel
import com.jarvis.chat.feature.ai.domain.repository.GatewayRepository

class GetGatewayAuditUseCase(
    private val repository: GatewayRepository,
) {

    suspend operator fun invoke(limit: Int): List<GatewayAuditEntryModel> = repository.loadAudit(limit)
}
