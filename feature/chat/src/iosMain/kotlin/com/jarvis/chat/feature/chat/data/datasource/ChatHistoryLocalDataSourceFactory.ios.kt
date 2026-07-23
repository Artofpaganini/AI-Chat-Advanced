package com.jarvis.chat.feature.chat.data.datasource

import com.jarvis.chat.feature.chat.domain.model.ChatStorageConfigModel
import kotlinx.coroutines.CoroutineDispatcher

internal actual fun createChatHistoryLocalDataSource(
    storageConfig: ChatStorageConfigModel,
    ioDispatcher: CoroutineDispatcher,
): ChatHistoryLocalDataSource = ChatHistoryLocalDataSourceImpl(
    storageConfig = storageConfig,
    ioDispatcher = ioDispatcher,
)
