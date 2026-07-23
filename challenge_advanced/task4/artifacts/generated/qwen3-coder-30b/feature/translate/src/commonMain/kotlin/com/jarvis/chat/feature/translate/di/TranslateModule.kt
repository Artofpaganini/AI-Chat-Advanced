package com.jarvis.chat.feature.translate.di

import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSource
import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSourceImpl
import com.jarvis.chat.feature.translate.data.repository.TranslateRepositoryImpl
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository
import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.TranslateViewModel
import org.koin.dsl.module

val translateModule = module {
    factory<TranslateRemoteDataSource> { TranslateRemoteDataSourceImpl(get(), get()) }
    factory<TranslateRepository> { TranslateRepositoryImpl(get()) }
    factory { TranslateTextUseCase(get()) }
    viewModel { TranslateViewModel(get()) }
}
