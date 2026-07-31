package com.jarvis.chat.feature.settings.di

import com.jarvis.chat.feature.settings.data.datasource.AiModelSettingsLocalDataSource
import com.jarvis.chat.feature.settings.data.datasource.AiModelSettingsLocalDataSourceImpl
import com.jarvis.chat.feature.settings.data.datasource.AiProviderSettingsLocalDataSource
import com.jarvis.chat.feature.settings.data.datasource.AiProviderSettingsLocalDataSourceImpl
import com.jarvis.chat.feature.settings.data.datasource.InferenceModeSettingsLocalDataSource
import com.jarvis.chat.feature.settings.data.datasource.InferenceModeSettingsLocalDataSourceImpl
import com.jarvis.chat.feature.settings.data.datasource.MicroModelFirstLocalDataSource
import com.jarvis.chat.feature.settings.data.datasource.MicroModelFirstLocalDataSourceImpl
import com.jarvis.chat.feature.settings.data.datasource.ThemeSettingsLocalDataSource
import com.jarvis.chat.feature.settings.data.datasource.ThemeSettingsLocalDataSourceImpl
import com.jarvis.chat.feature.settings.data.repository.AiModelSettingsRepositoryImpl
import com.jarvis.chat.feature.settings.data.repository.AiProviderSettingsRepositoryImpl
import com.jarvis.chat.feature.settings.data.repository.InferenceModeSettingsRepositoryImpl
import com.jarvis.chat.feature.settings.data.repository.MicroModelFirstSettingsRepositoryImpl
import com.jarvis.chat.feature.settings.data.repository.ThemeSettingsRepositoryImpl
import com.jarvis.chat.feature.settings.domain.repository.AiModelSettingsRepository
import com.jarvis.chat.feature.settings.domain.repository.AiProviderSettingsRepository
import com.jarvis.chat.feature.settings.domain.repository.InferenceModeSettingsRepository
import com.jarvis.chat.feature.settings.domain.repository.MicroModelFirstSettingsRepository
import com.jarvis.chat.feature.settings.domain.repository.ThemeSettingsRepository
import com.jarvis.chat.feature.settings.domain.usecase.ObserveAiModelUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveAiProviderUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveInferenceModeUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveMicroModelFirstEnabledUseCase
import com.jarvis.chat.feature.settings.domain.usecase.ObserveThemeModeUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveAiModelUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveAiProviderUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveInferenceModeUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveMicroModelFirstEnabledUseCase
import com.jarvis.chat.feature.settings.domain.usecase.SaveThemeModeUseCase
import com.jarvis.chat.feature.settings.presentation.SettingsViewModel
import com.jarvis.chat.feature.settings.presentation.mapper.SettingsUiMapper
import com.russhwolf.settings.Settings
import org.koin.core.module.Module
import org.koin.core.module.dsl.factoryOf
import org.koin.core.module.dsl.singleOf
import org.koin.core.module.dsl.viewModelOf
import org.koin.dsl.bind
import org.koin.dsl.module

val settingsModule: Module = module {
    single<Settings> { Settings() }
    singleOf(::ThemeSettingsLocalDataSourceImpl) bind ThemeSettingsLocalDataSource::class
    singleOf(::ThemeSettingsRepositoryImpl) bind ThemeSettingsRepository::class
    factoryOf(::ObserveThemeModeUseCase)
    factoryOf(::SaveThemeModeUseCase)
    singleOf(::AiModelSettingsLocalDataSourceImpl) bind AiModelSettingsLocalDataSource::class
    singleOf(::AiModelSettingsRepositoryImpl) bind AiModelSettingsRepository::class
    factoryOf(::ObserveAiModelUseCase)
    factoryOf(::SaveAiModelUseCase)
    singleOf(::AiProviderSettingsLocalDataSourceImpl) bind AiProviderSettingsLocalDataSource::class
    singleOf(::AiProviderSettingsRepositoryImpl) bind AiProviderSettingsRepository::class
    factoryOf(::ObserveAiProviderUseCase)
    factoryOf(::SaveAiProviderUseCase)
    singleOf(::MicroModelFirstLocalDataSourceImpl) bind MicroModelFirstLocalDataSource::class
    singleOf(::MicroModelFirstSettingsRepositoryImpl) bind MicroModelFirstSettingsRepository::class
    factoryOf(::ObserveMicroModelFirstEnabledUseCase)
    factoryOf(::SaveMicroModelFirstEnabledUseCase)
    singleOf(::InferenceModeSettingsLocalDataSourceImpl) bind InferenceModeSettingsLocalDataSource::class
    singleOf(::InferenceModeSettingsRepositoryImpl) bind InferenceModeSettingsRepository::class
    factoryOf(::ObserveInferenceModeUseCase)
    factoryOf(::SaveInferenceModeUseCase)
    factoryOf(::SettingsUiMapper)
    viewModelOf(::SettingsViewModel)
}
