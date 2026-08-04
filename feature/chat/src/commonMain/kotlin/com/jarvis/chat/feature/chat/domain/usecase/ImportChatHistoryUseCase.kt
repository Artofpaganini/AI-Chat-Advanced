package com.jarvis.chat.feature.chat.domain.usecase

import com.jarvis.chat.feature.ai.domain.model.InputGuardResultModel
import com.jarvis.chat.feature.ai.domain.usecase.CheckInputGuardUseCase
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.domain.model.ImportGuardSettingProvider
import com.jarvis.chat.feature.chat.domain.model.ImportOutcomeModel
import com.jarvis.chat.feature.chat.domain.model.ImportStrategy
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository

internal class ImportChatHistoryUseCase(
    private val repository: ChatHistoryRepository,
    private val checkInputGuardUseCase: CheckInputGuardUseCase,
    private val importGuardSettingProvider: ImportGuardSettingProvider,
) {

    suspend operator fun invoke(
        sessionId: String,
        json: String,
        strategy: ImportStrategy,
        current: List<HistoryMessageModel>,
    ): Result<ImportOutcomeModel> =
        runCatching {
            repository.importMessages(
                sessionId = sessionId,
                json = json,
                strategy = strategy,
                current = current,
                isProtectionEnabled = importGuardSettingProvider.isImportGuardEnabled(),
                isTextAllowed = { text -> checkInputGuardUseCase(text) !is InputGuardResultModel.Blocked },
            )
        }
}
