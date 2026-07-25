package com.jarvis.chat.feature.settings.di

import com.jarvis.chat.feature.settings.data.datasource.ThemeSettingsLocalDataSource
import com.jarvis.chat.feature.settings.data.datasource.ThemeSettingsLocalDataSourceImpl
import com.jarvis.chat.feature.settings.data.repository.ThemeSettingsRepositoryImpl
import com.jarvis.chat.feature.settings.domain.repository.ThemeSettingsRepository
import com.jarvis.chat.feature.settings.domain.usecase.ObserveThemeModeUseCase
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
    factoryOf(::SettingsUiMapper)
    viewModelOf(::SettingsViewModel)
}
