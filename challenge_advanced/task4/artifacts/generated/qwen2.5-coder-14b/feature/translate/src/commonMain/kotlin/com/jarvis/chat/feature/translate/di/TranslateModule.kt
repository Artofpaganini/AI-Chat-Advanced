package com.jarvis.chat.feature.translate.di

import com.jarvis.chat.AppConfig
import com.jarvis.chat.core.network.HttpClientFactory
import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSourceImpl
import com.jarvis.chat.feature.translate.data.repository.TranslateRepositoryImpl
import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.TranslateViewModel
import org.koin.dsl.module

val translateModule = module {
    factory { TranslateRemoteDataSourceImpl(get(), get()) }
    factory { TranslateRepositoryImpl(get()) }
    factory { TranslateTextUseCase(get()) }
    viewModel { TranslateViewModel(get()) }
}
