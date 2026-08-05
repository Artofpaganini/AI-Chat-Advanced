package com.jarvis.chat.feature.ai.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.GatewayStatsModel
import com.jarvis.chat.feature.ai.domain.repository.GatewayRepository

class GetGatewayStatsUseCase(
    private val repository: GatewayRepository,
) {

    suspend operator fun invoke(): GatewayStatsModel = repository.loadStats()
}
