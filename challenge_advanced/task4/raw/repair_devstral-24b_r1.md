```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/di/TranslateModule.kt
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

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/datasource/TranslateRemoteDataSource.kt
package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.body
import kotlinx.serialization.json.Json

internal interface TranslateRemoteDataSource {
    suspend fun translateText(request: TranslateRequestModel): TranslateResponseModel
}

internal class TranslateRemoteDataSourceImpl(
    private val client: HttpClient,
    private val baseUrl: String,
    private val apiKey: String
) : TranslateRemoteDataSource {

    override suspend fun translateText(request: TranslateRequestModel): TranslateResponseModel {
        return client.post("$baseUrl/chat/completions") {
            setBody(Json.encodeToString(TranslateRequestModel.serializer(), request))
            header("Authorization", "Bearer $apiKey")
        }.body<TranslateResponseModel>()
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/datasource/TranslateRemoteDataSourceImpl.kt
package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.body
import kotlinx.serialization.json.Json

internal class TranslateRemoteDataSourceImpl(
    private val client: HttpClient,
    private val baseUrl: String,
    private val apiKey: String
) : TranslateRemoteDataSource {

    override suspend fun translateText(request: TranslateRequestModel): TranslateResponseModel {
        return client.post("$baseUrl/chat/completions") {
            setBody(Json.encodeToString(TranslateRequestModel.serializer(), request))
            header("Authorization", "Bearer $apiKey")
        }.body<TranslateResponseModel>()
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/repository/TranslateRepositoryImpl.kt
package com.jarvis.chat.feature.translate.data.repository

import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSource
import com.jarvis.chat.feature.translate.data.mapper.toTranslationModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository

internal class TranslateRepositoryImpl(
    private val remoteDataSource: TranslateRemoteDataSource
) : TranslateRepository {

    override suspend fun translateText(sourceText: String, targetLanguage: TargetLanguage): TranslationModel {
        val request = TranslateRequestModel(
            model = "deepseek-chat",
            messages = listOf(TranslateMessageRequestModel(role = "user", content = sourceText))
        )
        val response = remoteDataSource.translateText(request)
        return response.toTranslationModel()
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/mapper/TranslateResponseMapper.kt
package com.jarvis.chat.feature.translate.data.mapper

import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal fun TranslateResponseModel.toTranslationModel(): TranslationModel {
    val translatedText = choices.firstOrNull()?.message?.content.orEmpty()
    return TranslationModel(sourceText = "", translatedText = translatedText)
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateResponseModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateResponseModel(
    val choices: List<TranslateChoiceResponseModel>
)

@Serializable
internal data class TranslateChoiceResponseModel(
    val message: TranslateMessageResponseModel
)

@Serializable
internal data class TranslateMessageResponseModel(
    val role: String,
    val content: String
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateRequestModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateRequestModel(
    val model: String,
    val messages: List<TranslateMessageRequestModel>
)

@Serializable
internal data class TranslateMessageRequestModel(
    val role: String,
    val content: String
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateMessageResponseModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateMessageResponseModel(
    val role: String,
    val content: String
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateMessageRequestModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateMessageRequestModel(
    val role: String,
    val content: String
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateChoiceResponseModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateChoiceResponseModel(
    val message: TranslateMessageResponseModel
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/repository/TranslateRepository.kt
package com.jarvis.chat.feature.translate.domain.repository

import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal interface TranslateRepository {
    suspend fun translateText(sourceText: String, targetLanguage: TargetLanguage): TranslationModel
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/model/TargetLanguage.kt
package com.jarvis.chat.feature.translate.domain.model

internal enum class TargetLanguage {
    ENGLISH, SPANISH, FRENCH, GERMAN, CHINESE
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/model/TranslationModel.kt
package com.jarvis.chat.feature.translate.domain.model

internal data class TranslationModel(
    val sourceText: String,
    val translatedText: String,
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/usecase/TranslateTextUseCase.kt
package com.jarvis.chat.feature.translate.domain.usecase

import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository

internal class TranslateTextUseCase(
    private val repository: TranslateRepository
) {
    suspend operator fun invoke(sourceText: String, targetLanguage: TargetLanguage): TranslationModel {
        return repository.translateText(sourceText, targetLanguage)
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/TranslateScreen.kt
package com.jarvis.chat.feature.translate.presentation

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.jarvis.chat.core.viewmodel.UdfViewModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

@Composable
internal fun TranslateScreen(viewModel: UdfViewModel<TranslateAction, TranslateUiModel>) {
    val uiState = viewModel.uiState.collectAsState().value

    Scaffold(
        topBar = { TopAppBar(title = { Text("Translate") }) }
    ) { padding ->
        Column(modifier = Modifier.padding(padding)) {
            OutlinedTextField(
                value = uiState.sourceText,
                onValueChange = { viewModel.onAction(TranslateAction.Ui(TranslateAction.UiAction.OnTranslate(it, TargetLanguage.ENGLISH))) },
                label = { Text("Source Text") }
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = uiState.translatedText,
                onValueChange = {},
                label = { Text("Translated Text") },
                readOnly = true
            )
            if (uiState.isLoading) {
                CircularProgressIndicator()
            }
            if (uiState.errorMessage != null) {
                Text(text = uiState.errorMessage, color = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@Preview
@Composable
private fun TranslateScreenPreview() {
    // Preview implementation here
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/TranslateViewModel.kt
package com.jarvis.chat.feature.translate.presentation

import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.mapper.TranslateUiMapper
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateEvent
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

internal class TranslateViewModel(
    private val translateTextUseCase: TranslateTextUseCase
) : UdfBaseViewModel<TranslateAction, TranslateUiModel, TranslateState, TranslateEvent>(
    initialState = TranslateState(),
    uiMapper = TranslateUiMapper()
) {

    override fun onAction(action: TranslateAction) {
        when (action) {
            is TranslateAction.Ui -> handleUiAction(action.action)
            is TranslateAction.Internal -> handleInternalAction(action.action)
        }
    }

    private fun handleUiAction(action: TranslateAction.UiAction) {
        when (action) {
            is TranslateAction.UiAction.OnTranslate -> {
                updateState { copy(sourceText = action.sourceText, targetLanguage = action.targetLanguage, isLoading = true, errorMessage = null) }
                onInternal(TranslateAction.Internal.LoadTranslation)
            }
        }
    }

    private fun handleInternalAction(action: TranslateAction.InternalAction) {
        when (action) {
            is TranslateAction.InternalAction.LoadTranslation -> {
                try {
                    val translation = translateTextUseCase(currentState.sourceText, currentState.targetLanguage!!)
                    updateState { copy(translatedText = translation.translatedText, isLoading = false) }
                } catch (e: Exception) {
                    postEvent(TranslateEvent.ShowError(e.message ?: "Unknown error"))
                    updateState { copy(isLoading = false, errorMessage = e.message) }
                }
            }
        }
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/mapper/TranslateUiMapper.kt
package com.jarvis.chat.feature.translate.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

internal class TranslateUiMapper : UiMapper<TranslateState, TranslateUiModel> {
    override fun map(state: TranslateState): TranslateUiModel {
        return TranslateUiModel(
            sourceText = state.sourceText,
            targetLanguage = state.targetLanguage,
            translatedText = state.translatedText,
            isLoading = state.isLoading,
            errorMessage = state.errorMessage
        )
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateState.kt
package com.jarvis.chat.feature.translate.presentation.model

internal data class TranslateState(
    val sourceText: String = "",
    val targetLanguage: TargetLanguage? = null,
    val translatedText: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateUiModel.kt
package com.jarvis.chat.feature.translate.presentation.model

internal data class TranslateUiModel(
    val sourceText: String,
    val targetLanguage: TargetLanguage?,
    val translatedText: String,
    val isLoading: Boolean,
    val errorMessage: String?
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateAction.kt
package com.jarvis.chat.feature.translate.presentation.model

internal sealed interface TranslateAction {
    data class Ui(val action: UiAction) : TranslateAction
    data class Internal(val action: InternalAction) : TranslateAction

    sealed interface UiAction {
        data class OnTranslate(val sourceText: String, val targetLanguage: TargetLanguage) : UiAction
    }

    sealed interface InternalAction {
        object LoadTranslation : InternalAction
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateEvent.kt
package com.jarvis.chat.feature.translate.presentation.model

internal sealed interface TranslateEvent {
    data class ShowError(val message: String) : TranslateEvent
}
```