package com.jarvis.chat.feature.ai.data.repository

import com.jarvis.chat.feature.ai.data.datasource.GatewayRemoteDataSource
import com.jarvis.chat.feature.ai.data.mapper.toGatewayAuditEntryModel
import com.jarvis.chat.feature.ai.data.mapper.toGatewayLoadErrorModel
import com.jarvis.chat.feature.ai.data.mapper.toGatewayStatsModel
import com.jarvis.chat.feature.ai.domain.model.GatewayAuditEntryModel
import com.jarvis.chat.feature.ai.domain.model.GatewayLoadException
import com.jarvis.chat.feature.ai.domain.model.GatewayStatsModel
import com.jarvis.chat.feature.ai.domain.repository.GatewayRepository
import kotlinx.coroutines.CancellationException

internal class GatewayRepositoryImpl(
    private val remoteDataSource: GatewayRemoteDataSource,
) : GatewayRepository {

    @Suppress("TooGenericExceptionCaught")
    override suspend fun loadAudit(limit: Int): List<GatewayAuditEntryModel> =
        try {
            remoteDataSource.requestAudit(limit).map { entry -> entry.toGatewayAuditEntryModel() }
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (throwable: Throwable) {
            throw GatewayLoadException(error = throwable.toGatewayLoadErrorModel())
        }

    @Suppress("TooGenericExceptionCaught")
    override suspend fun loadStats(): GatewayStatsModel =
        try {
            remoteDataSource.requestStats().toGatewayStatsModel()
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (throwable: Throwable) {
            throw GatewayLoadException(error = throwable.toGatewayLoadErrorModel())
        }
}
