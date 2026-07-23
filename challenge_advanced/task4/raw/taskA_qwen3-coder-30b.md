```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateRequestModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateRequestModel(
    val model: String = "deepseek-chat",
    val messages: List<TranslateMessageRequestModel>,
)
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateMessageRequestModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateMessageRequestModel(
    val role: String,
    val content: String,
)
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateResponseModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateResponseModel(
    val choices: List<TranslateChoiceResponseModel>,
)
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateChoiceResponseModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateChoiceResponseModel(
    val message: TranslateMessageResponseModel,
)
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/model/TranslateMessageResponseModel.kt
package com.jarvis.chat.feature.translate.data.model

import kotlinx.serialization.Serializable

@Serializable
internal data class TranslateMessageResponseModel(
    val role: String,
    val content: String,
)
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/mapper/TranslateResponseMapper.kt
package com.jarvis.chat.feature.translate.data.mapper

import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal fun TranslateResponseModel.toTranslationModel(): TranslationModel =
    TranslationModel(
        sourceText = "",
        translatedText = choices.firstOrNull()?.message?.content.orEmpty(),
    )
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/datasource/TranslateRemoteDataSource.kt
package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel

internal interface TranslateRemoteDataSource {
    suspend fun translate(request: TranslateRequestModel): TranslateResponseModel
}
```

---- ход ----

```kotlin
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
```

---- ход ----

```kotlin
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
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/model/TranslationModel.kt
package com.jarvis.chat.feature.translate.domain.model

internal data class TranslationModel(
    val sourceText: String,
    val translatedText: String,
)
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/model/TargetLanguage.kt
package com.jarvis.chat.feature.translate.domain.model

internal enum class TargetLanguage {
    ENGLISH,
    RUSSIAN,
    FRENCH,
    SPANISH,
    GERMAN,
}
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/repository/TranslateRepository.kt
package com.jarvis.chat.feature.translate.domain.repository

import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage

internal interface TranslateRepository {
    suspend fun translate(text: String, targetLanguage: String): TranslationModel
}
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/usecase/TranslateTextUseCase.kt
package com.jarvis.chat.feature.translate.domain.usecase

import com.jarvis.chat.feature.translate.domain.model.TranslationModel
import com.jarvis.chat.feature.translate.domain.repository.TranslateRepository

internal class TranslateTextUseCase(
    private val repository: TranslateRepository,
) {
    suspend operator fun invoke(text: String, targetLanguage: String): TranslationModel {
        return repository.translate(text, targetLanguage)
    }
}
```

---- ход ----

```kotlin
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
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateState.kt
package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal data class TranslateState(
    val translation: TranslationModel? = null,
    val isLoading: Boolean = false,
    val error: String? = null,
)
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateEvent.kt
package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.core.viewmodel.Event

internal sealed interface TranslateEvent : Event {
    data class ShowError(val message: String) : TranslateEvent
}
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/model/TranslateUiModel.kt
package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal data class TranslateUiModel(
    val translation: TranslationModel? = null,
    val isLoading: Boolean = false,
    val error: String? = null,
)
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/mapper/TranslateUiMapper.kt
package com.jarvis.chat.feature.translate.presentation.mapper

import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel
import com.jarvis.chat.core.viewmodel.UiMapper

internal class TranslateUiMapper : UiMapper<TranslateState, TranslateUiModel> {
    override fun map(state: TranslateState): TranslateUiModel =
        TranslateUiModel(
            translation = state.translation,
            isLoading = state.isLoading,
            error = state.error,
        )
}
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/TranslateViewModel.kt
package com.jarvis.chat.feature.translate.presentation

import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateEvent
import com.jarvis.chat.feature.translate.presentation.model.TranslateState
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel
import com.jarvis.chat.core.viewmodel.UdfBaseViewModel

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
```

---- ход ----

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/TranslateScreen.kt
package com.jarvis.chat.feature.translate.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction

@Composable
internal fun TranslateScreen(viewModel: TranslateViewModel) {
    var inputText by remember { mutableStateOf("") }
    var targetLanguage by remember { mutableStateOf("ru") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        OutlinedTextField(
            value = inputText,
            onValueChange = { inputText = it },
            label = { Text("Enter text to translate") },
            modifier = Modifier.fillMaxWidth()
        )

        OutlinedTextField(
            value = targetLanguage,
            onValueChange = { targetLanguage = it },
            label = { Text("Target language") },
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Text)
        )

        Button(
            onClick = {
                viewModel.onAction(TranslateAction.Translate(inputText, targetLanguage))
            }
        ) {
            Text("Translate")
        }

        // TODO: Add error handling and loading indicator
    }
}
```

---- ход ----

```kotlin
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
```