Сгенерируй новую фичу `translate` для проекта JarvisChat.

Что делает фича: пользователь вводит текст и выбирает целевой язык, приложение отправляет запрос в DeepSeek
и показывает перевод. Ошибку сети показываем в UI, приложение не падает.

## Технические факты проекта (используй как есть, не выдумывай свои)

- Пакет фичи: `com.jarvis.chat.feature.translate`, каталог `feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/`.
- Базовый класс: `com.jarvis.chat.core.viewmodel.UdfBaseViewModel<Action, UiState, State, Event>`.
  У него есть `updateState { copy(...) }`, `postEvent(event)`, `currentState`, абстрактный `onAction(action)`.
- Интерфейс маппера: `com.jarvis.chat.core.viewmodel.UiMapper<State, UiState>` с методом `fun map(state: State): UiState`.
- Сеть: Ktor client, `io.ktor.client.HttpClient`, `post`, `setBody`, `body<T>()`, kotlinx.serialization.
- Endpoint DeepSeek: `POST https://api.deepseek.com/chat/completions`, тело `{"model": "deepseek-chat", "messages": [...]}`,
  ответ `{"choices": [{"message": {"role": ..., "content": ...}}]}`, заголовок `Authorization: Bearer <ключ>`.
- Ключ и базовый URL берутся из `com.jarvis.chat.AppConfig` (поля `deepSeekApiKey`, `deepSeekBaseUrl`), приходит через Koin.
- DI: Koin DSL, `val translateModule = module { ... }`, фабрики через `factory`, ViewModel через `viewModel`.
- UI: Compose Multiplatform + Material3.

## Что должно получиться

Файлы ровно в этих под-каталогах:

```
data/model/        TranslateRequestModel, TranslateMessageRequestModel, TranslateResponseModel, TranslateChoiceResponseModel, TranslateMessageResponseModel
data/mapper/       TranslateResponseMapper (extension toTranslationModel)
data/datasource/   TranslateRemoteDataSource + TranslateRemoteDataSourceImpl
data/repository/   TranslateRepositoryImpl
domain/model/      TranslationModel, TargetLanguage (enum)
domain/repository/ TranslateRepository
domain/usecase/    TranslateTextUseCase
presentation/model/   TranslateAction, TranslateState, TranslateEvent, TranslateUiModel
presentation/mapper/  TranslateUiMapper
presentation/         TranslateViewModel, TranslateScreen
di/                   TranslateModule
```

## Формат ответа

Никаких объяснений до и после. Только файлы, каждый отдельным блоком, первая строка блока - путь:

```kotlin
// path: feature/translate/src/commonMain/kotlin/com/jarvis/chat/feature/translate/domain/model/TranslationModel.kt
package com.jarvis.chat.feature.translate.domain.model

internal data class TranslationModel(
    val sourceText: String,
    val translatedText: String,
)
```

Выдай все файлы за один ответ.
