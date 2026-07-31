package com.jarvis.chat.core.micromodel.di

import com.jarvis.chat.core.micromodel.data.datasource.MicroModelConfigLocalDataSource
import com.jarvis.chat.core.micromodel.data.datasource.MicroModelConfigLocalDataSourceImpl
import com.jarvis.chat.core.micromodel.data.repository.MicroModelRepositoryImpl
import com.jarvis.chat.core.micromodel.domain.repository.MicroModelRepository
import com.jarvis.chat.core.micromodel.domain.usecase.ClassifyMessageUseCase
import org.koin.core.module.Module
import org.koin.core.module.dsl.factoryOf
import org.koin.core.module.dsl.singleOf
import org.koin.dsl.bind
import org.koin.dsl.module

val microModelModule: Module = module {
    singleOf(::MicroModelConfigLocalDataSourceImpl) bind MicroModelConfigLocalDataSource::class
    singleOf(::MicroModelRepositoryImpl) bind MicroModelRepository::class
    factoryOf(::ClassifyMessageUseCase)
}
