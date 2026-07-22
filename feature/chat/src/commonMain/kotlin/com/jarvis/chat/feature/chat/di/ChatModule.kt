package com.jarvis.chat.feature.chat.di

import com.jarvis.chat.feature.ai.di.aiModule
import com.jarvis.chat.feature.chat.data.datasource.ChatHistoryLocalDataSource
import com.jarvis.chat.feature.chat.data.datasource.ChatHistoryLocalDataSourceImpl
import com.jarvis.chat.feature.chat.data.repository.ChatHistoryRepositoryImpl
import com.jarvis.chat.feature.chat.domain.model.ChatStorageConfigModel
import com.jarvis.chat.feature.chat.domain.repository.ChatHistoryRepository
import com.jarvis.chat.feature.chat.domain.usecase.ExportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.ImportChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.LoadChatHistoryUseCase
import com.jarvis.chat.feature.chat.domain.usecase.SaveChatHistoryUseCase
import com.jarvis.chat.feature.chat.presentation.ChatViewModel
import com.jarvis.chat.feature.chat.presentation.mapper.ChatUiMapper
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import org.koin.core.module.Module
import org.koin.core.module.dsl.factoryOf
import org.koin.core.module.dsl.singleOf
import org.koin.core.module.dsl.viewModelOf
import org.koin.dsl.bind
import org.koin.dsl.module

fun chatModule(storageDirectoryPath: String): Module = module {
    includes(aiModule)
    single { ChatStorageConfigModel(directoryPath = storageDirectoryPath) }
    single<CoroutineDispatcher> { Dispatchers.Default }
    singleOf(::ChatHistoryLocalDataSourceImpl) bind ChatHistoryLocalDataSource::class
    singleOf(::ChatHistoryRepositoryImpl) bind ChatHistoryRepository::class
    factoryOf(::LoadChatHistoryUseCase)
    factoryOf(::SaveChatHistoryUseCase)
    factoryOf(::ExportChatHistoryUseCase)
    factoryOf(::ImportChatHistoryUseCase)
    factoryOf(::ChatUiMapper)
    viewModelOf(::ChatViewModel)
}
