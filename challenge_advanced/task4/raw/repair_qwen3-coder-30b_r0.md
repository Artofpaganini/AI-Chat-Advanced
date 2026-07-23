// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/datasource/TranslateRemoteDataSourceImpl.kt
package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.AppConfig
import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import io.ktor.client.HttpClient
import io.ktor.client.request.headers
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import io.ktor.client.call.body

internal class TranslateRemoteDataSourceImpl(
    private val client: HttpClient,
    private val appConfig: AppConfig,
) : TranslateRemoteDataSource {
    override suspend fun translate(request: TranslateRequestModel): TranslateResponseModel {
        return client.post("${appConfig.deepSeekBaseUrl}/chat/completions") {
            headers {
                append(HttpHeaders.Authorization, "Bearer ${appConfig.deepSeekApiKey}")
                contentType(ContentType.Application.Json)
            }
            setBody(request)
        }.body()
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/repository/TranslateRepositoryImpl.kt
package com.jarvis.chat.feature.translate.data.repository

import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSource
import com.jarvis.chat.feature.translate.data.mapper.toTranslationModel
import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository

internal class TranslateRepositoryImpl(
    private val remoteDataSource: TranslateRemoteDataSource,
) : TranslateRepository {
    override suspend fun translate(text: String, targetLanguage: String): TranslationModel {
        val request = TranslateRequestModel(
            messages = listOf(
                TranslateRequestModel.TranslateMessageRequestModel(
                    role = "user",
                    content = "Translate the following text to $targetLanguage: $text"
                )
            )
        )
        return remoteDataSource.translate(request).toTranslationModel()
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/di/TranslateModule.kt
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

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/TranslateViewModel.kt
package com.jarvis.chat.feature.translate.presentation

import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateEvent
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import kotlinx.coroutines.launch

internal class TranslateViewModel(
    private val translateText: TranslateTextUseCase,
) : UdfBaseViewModel<TranslateAction, TranslateUiModel, TranslateState, TranslateEvent>(
    initialState = TranslateState(),
    uiMapper = TranslateUiMapper(),
) {
    override fun onAction(action: TranslateAction) {
        when (action) {
            is TranslateAction.Translate -> {
                updateState { copy(isLoading = true, error = null) }
                viewModelScope.launch {
                    try {
                        val result = translateText(action.text, action.targetLanguage)
                        updateState {
                            copy(
                                isLoading = false,
                                translation = result,
                            )
                        }
                    } catch (e: Exception) {
                        updateState {
                            copy(
                                isLoading = false,
                                error = e.message,
                            )
                        }
                        postEvent(TranslateEvent.ShowError(e.message ?: "Unknown error"))
                    }
                }
            }
            TranslateAction.Clear -> {
                updateState { copy(translation = null, error = null) }
            }
        }
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateAction.kt
package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.core.viewmodel.Action

internal sealed interface TranslateAction : Action {
    data class Translate(
        val text: String,
        val targetLanguage: String,
    ) : TranslateAction

    object Clear : TranslateAction
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateEvent.kt
package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.core.viewmodel.Event

internal sealed interface TranslateEvent : Event {
    data class ShowError(val message: String) : TranslateEvent
}