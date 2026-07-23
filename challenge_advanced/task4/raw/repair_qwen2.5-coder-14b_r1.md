```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/di/TranslateModule.kt
package com.jarvis.chat.feature.translate.di

import com.jarvis.chat.AppConfig
import com.jarvis.chat.core.network.HttpClientFactory
import com.jarvis.chat.feature.translate.data.datasource.TranslateRemoteDataSourceImpl
import com.jarvis.chat.feature.translate.data.repository.TranslateRepositoryImpl
import com.jarvis.chat.feature.translate.domain.usecase.TranslateTextUseCase
import com.jarvis.chat.feature.translate.presentation.TranslateViewModel
import org.koin.dsl.module

val translateModule = module {
    single { HttpClientFactory.create() }
    factory { AppConfig() }
    factory { TranslateRemoteDataSourceImpl(get(), get()) }
    factory { TranslateRepositoryImpl(get()) }
    factory { TranslateTextUseCase(get()) }
    viewModel { (translateText: TranslateTextUseCase) -> TranslateViewModel(translateText) }
}
```

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/data/datasource/TranslateRemoteDataSourceImpl.kt
package com.jarvis.chat.feature.translate.data.datasource

import com.jarvis.chat.AppConfig
import com.jarvis.chat.feature.translate.data.model.TranslateRequestModel
import com.jarvis.chat.feature.translate.data.model.TranslateResponseModel
import io.ktor.client.HttpClient
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.readText

internal class TranslateRemoteDataSourceImpl(
    private val client: HttpClient,
    private val appConfig: AppConfig,
) : TranslateRemoteDataSource {

    override suspend fun translate(request: TranslateRequestModel): TranslateResponseModel {
        return client.post("${appConfig.deepSeekBaseUrl}/chat/completions") {
            setBody(request)
            headers.append("Authorization", "Bearer ${appConfig.deepSeekApiKey}")
        }.readText().let { response ->
            kotlinx.serialization.json.Json.decodeFromString(TranslateResponseModel.serializer(), response)
        }
    }
}
```

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

    override suspend fun translateText(sourceText: String, targetLanguage: TargetLanguage): TranslationModel {
        val request = TranslateRequestModel(
            model = "deepseek-chat",
            messages = listOf(
                TranslateMessageRequestModel(
                    role = "user",
                    content = sourceText,
                ),
            ),
        )
        return remoteDataSource.translate(request).toTranslationModel()
    }
}
```

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/TranslateScreen.kt
package com.jarvis.chat.feature.translate.presentation

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.jarvis.chat.core.viewmodel.collectAsStateWithLifecycle
import com.jarvis.chat.feature.translate.domain.model.TargetLanguage
import com.jarvis.chat.feature.translate.presentation.model.TranslateAction
import com.jarvis.chat.feature.translate.presentation.model.TranslateUiModel

@Composable
fun TranslateScreen(viewModel: TranslateViewModel) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        TextField(
            value = uiState.sourceText,
            onValueChange = { viewModel.onAction(TranslateAction.Ui.InputText(it)) },
            label = { Text("Enter text to translate") },
            modifier = Modifier.fillMaxWidth(),
        )

        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            TargetLanguage.values().forEach { language ->
                Button(onClick = { viewModel.onAction(TranslateAction.Ui.SelectLanguage(language)) }) {
                    Text(text = language.name)
                }
            }
        }

        Button(onClick = { viewModel.onAction(TranslateAction.Ui.Translate) }) {
            Text("Translate")
        }

        uiState.translationModel?.let {
            Text(text = "Translated: ${it.translatedText}")
        }

        uiState.errorMessage?.let {
            Text(text = it, color = MaterialTheme.colorScheme.error)
        }
    }
}
```

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/presentation/TranslateViewModel.kt
package com.jarvis.chat.feature.translate.presentation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
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
    uiMapper = TranslateUiMapper(),
) {

    override fun onAction(action: TranslateAction) {
        when (action) {
            is TranslateAction.Ui.InputText -> updateState { copy(sourceText = action.text) }
            is TranslateAction.Ui.SelectLanguage -> updateState { copy(targetLanguage = action.language) }
            TranslateAction.Ui.Translate -> translate()
            is TranslateAction.Internal.TranslationResult -> updateState { copy(translationModel = action.translationModel, errorMessage = null) }
            is TranslateAction.Internal.Error -> postEvent(TranslateEvent.ShowError(action.message))
        }
    }

    private fun translate() {
        val sourceText = currentState.sourceText
        val targetLanguage = currentState.targetLanguage

        if (sourceText.isNotEmpty()) {
            viewModelScope.launch {
                try {
                    val translationModel = translateText.execute(sourceText, targetLanguage)
                    updateState { copy(translationModel = translationModel) }
                } catch (e: Exception) {
                    postEvent(TranslateEvent.ShowError(e.message ?: "An error occurred"))
                }
            }
        }
    }
}
```