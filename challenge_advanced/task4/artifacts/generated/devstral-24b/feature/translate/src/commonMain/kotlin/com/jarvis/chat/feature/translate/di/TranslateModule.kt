package com.jarvis.chat.feature.translate.di

import com.jarvis.chat.AppConfig
import com.jarvis.chat.core.viewmodel.UdfViewModel
import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSource
import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSourceImpl
import com.jarvis.chat.feature.translate.data.repository.TranslateRepositoryImpl
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository
import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.TranslateViewModel
import io.ktor.client.HttpClient
import org.koin.dsl.module

internal val translateModule = module {
    factory<TranslateRemoteDataSource> { TranslateRemoteDataSourceImpl(get(), get().deepSeekBaseUrl, get().deepSeekApiKey) }
    factory<TranslateRepository> { TranslateRepositoryImpl(get()) }
    factory { TranslateTextUseCase(get()) }
    viewModel { TranslateViewModel(get()) }
}
