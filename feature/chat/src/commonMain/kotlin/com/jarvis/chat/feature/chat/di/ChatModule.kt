package com.jarvis.chat.feature.chat.di

import com.jarvis.chat.feature.ai.di.aiModule
import com.jarvis.chat.feature.chat.presentation.ChatViewModel
import com.jarvis.chat.feature.chat.presentation.mapper.ChatUiMapper
import org.koin.core.module.Module
import org.koin.core.module.dsl.factoryOf
import org.koin.core.module.dsl.viewModelOf
import org.koin.dsl.module

val chatModule: Module = module {
    includes(aiModule)
    factoryOf(::ChatUiMapper)
    viewModelOf(::ChatViewModel)
}
