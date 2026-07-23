 ```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/datasource/TranslateRemoteDataSource.kt
package com.jarvis.chat.feature.translate.data.datasource

import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.request.url
import kotlinx.serialization.json.JsonObject

internal interface TranslateRemoteDataSource {
    suspend fun translate(text: String, targetLanguage: String): JsonObject?
}

internal class TranslateRemoteDataSourceImpl(private val client: HttpClient) : TranslateRemoteDataSource {
    override suspend fun translate(text: String, targetLanguage: String): JsonObject? {
        val requestModel = com.jarvis.chat.feature.translate.data.model.TranslateRequestModel(sourceText = text, targetLanguage = targetLanguage)
        return client.post("${AppConfig.deepSeekBaseUrl}/chat/completions") {
            setBody(requestModel)
        }.body()
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/datasource/TranslateRemoteDataSourceImpl.kt
package com.jarvis.chat.feature.translate.data.datasource

import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import kotlinx.serialization.json.JsonObject

internal class TranslateRemoteDataSourceImpl(private val client: HttpClient) : TranslateRemoteDataSource {
    override suspend fun translate(text: String, targetLanguage: String): JsonObject? = client.post("${AppConfig.deepSeekBaseUrl}/chat/completions") {
        setBody(com.jarvis.chat.feature.translate.data.model.TranslateRequestModel(sourceText = text, targetLanguage = targetLanguage))
    }.body()
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/repository/TranslateRepositoryImpl.kt
package com.jarvis.chat.feature.translate.data.repository

import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSource
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

internal class TranslateRepositoryImpl(private val dataSource: TranslateRemoteDataSource) : TranslateRepository {
    override suspend fun translateText(text: String, targetLanguage: com.jarvis.chat.feature.translate.domain.model.TargetLanguage): Flow<TranslationModel> = flow {
        val response = dataSource.translate(text, targetLanguage.name) ?: throw NetworkErrorException()
        emit(response.toTranslationModel())
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/mapper/TranslateResponseMapper.kt
package com.jarvis.chat.feature.translate.data.mapper

import com.jarvis.chat.feature.translate.data.model.TranslateChoiceResponseModel
import com.jarvis.chat.feature.translate.data.model.TranslateMessageResponseModel
import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage

internal fun TranslateChoiceResponseModel?.toTranslationModel(): TranslationModel {
    val content = this?.message?.content ?: ""
    return TranslationModel(sourceText = content, translatedText = content)
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateResponseModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateResponseModel(
    val choices: List<TranslateChoiceResponseModel>
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateRequestModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateRequestModel(
    val sourceText: String,
    val targetLanguage: String,
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateMessageResponseModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateMessageResponseModel(
    val role: String,
    val content: String,
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateMessageRequestModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateMessageRequestModel(
    val role: String,
    val content: String,
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateChoiceResponseModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateChoiceResponseModel(
    val message: TranslateMessageResponseModel?
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/repository/TranslateRepository.kt
package com.jarvis.chat.feature.translate.domain.repository

import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import kotlinx.coroutines.flow.Flow

internal interface TranslateRepository {
    suspend fun translateText(text: String, targetLanguage: TargetLanguage): Flow<TranslationModel>
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/model/TargetLanguage.kt
package com.jarvis.chat.feature.translate.domain.model

internal enum class TargetLanguage {
    EN, ES, FR, DE, JA, ZH
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/model/TranslationModel.kt
package com.jarvis.chat.feature.translate.domain.model

internal data class TranslationModel(
    val sourceText: String,
    val translatedText: String,
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/usecase/TranslateTextUseCase.kt
package com.jarvis.chat.feature.translate.domain.usecase

import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

internal class TranslateTextUseCase(private val repository: TranslateRepository) {
    operator fun invoke(text: String, targetLanguage: TargetLanguage): Flow<TranslationModel> = repository.translateText(text, targetLanguage).map { it }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/TranslateScreen.kt
package com.jarvis.chat.feature.translate.presentation

import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import org.koin.androidx.compose.viewModel

@Composable
fun TranslateScreen() {
    val viewModel = viewModel<TranslateViewModel>()
}

@Preview
@Composable
fun PreviewTranslateScreen() {
    TranslateScreen()
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/TranslateViewModel.kt
package com.jarvis.chat.feature.translate.presentation

import androidx.lifecycle.viewModelScope
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel
import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateEvent
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import kotlinx.coroutines.launch

internal class TranslateViewModel(
    private val translateText: TranslateTextUseCase,
) : UdfBaseViewModel<TranslateAction, TranslateUiModel, TranslateState, TranslateEvent>(
    initialState = TranslateState(),
    uiMapper = TranslateUiMapper()
) {
    override fun onAction(action: TranslateAction) {
        when (action) {
            is TranslateAction.Translate -> translate(action.text, action.targetLanguage)
        }
    }

    private fun translate(text: String, targetLanguage: String) {
        viewModelScope.launch {
            updateState { copy(isLoading = true) }
            try {
                val result = translateText(text, TargetLanguage.valueOf(targetLanguage)).first()
                postEvent(TranslateEvent.Translated(result.translatedText ?: ""))
            } catch (e: Exception) {
                updateState { copy(errorMessage = e.message ?: "Unknown error") }
            } finally {
                updateState { copy(isLoading = false) }
            }
        }
    }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/di/TranslateModule.kt
package com.jarvis.chat.feature.translate.di

import org.koin.dsl.module
import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSourceImpl
import com.jarvis.chat.feature.translate.data.repository.TranslateRepositoryImpl
import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.TranslateViewModel

val translateModule = module {
    factory { TranslateRemoteDataSourceImpl(get()) }
    factory { TranslateRepositoryImpl(get()) }
    factory { TranslateTextUseCase(get()) }
    viewModel { TranslateViewModel(get()) }
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/mapper/TranslateUiMapper.kt
package com.jarvis.chat.feature.translate.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

internal class TranslateUiMapper : UiMapper<TranslateState, TranslateUiModel> {
    override fun map(state: TranslateState): TranslateUiModel = TranslateUiModel(translatedText = state.isLoading)
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateState.kt
package com.jarvis.chat.feature.translate.presentation.model

internal data class TranslateState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateUiModel.kt
package com.jarvis.chat.feature.translate.presentation.model

internal data class TranslateUiModel(
    val translatedText: String? = null,
)

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateAction.kt
package com.jarvis.chat.feature.translate.presentation.model

internal sealed interface TranslateAction {
    data class Translate(val text: String, val targetLanguage: String) : TranslateAction
}

// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateEvent.kt
package com.jarvis.chat.feature.translate.presentation.model

internal sealed interface TranslateEvent {
    data class Translated(val translatedText: String) : TranslateEvent
}
```