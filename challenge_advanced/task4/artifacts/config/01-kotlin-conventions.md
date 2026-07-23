---
name: JarvisChat Kotlin conventions
alwaysApply: true
---

You write Kotlin for JarvisChat: Kotlin Multiplatform + Compose Multiplatform (Android, iOS, wasmJs).
Stack: Ktor client, kotlinx.serialization, Koin, kotlinx.coroutines, Clean Architecture + UDF.
Answer in Russian, write code and identifiers in English.

# Layers and file layout

Feature lives in `feature/<name>/`, package `com.jarvis.chat.feature.<name>`:

```
data/model/        *RequestModel / *ResponseModel / *DataModel   (@Serializable)
data/datasource/   *RemoteDataSource, *LocalDataSource (+Impl)
data/mapper/       toXxxModel() top-level extension functions
data/repository/   *RepositoryImpl
domain/model/      *Model
domain/repository/ *Repository (interface)
domain/usecase/    *UseCase
presentation/model/   *Action / *State / *Event / *UiModel
presentation/mapper/  *UiMapper : UiMapper<State, UiModel>
presentation/         *ViewModel.kt, *Screen.kt
di/                *Module.kt (Koin)
```

One entity per file, in its own subdirectory. Never flatten these into one file.

# STRICT naming

- data layer: `*RequestModel`, `*ResponseModel`, `*DataModel`.
- domain layer: `*Model`.
- presentation layer: `*UiModel`.
- The word `Dto` is forbidden everywhere: classes, files, packages.
- Bare `*Request` / `*Response` without the `Model` suffix are forbidden.
- A class named `*UiState` is forbidden. The UI model is `*UiModel`.

# UDF

ViewModel extends `UdfBaseViewModel<Action, UiState, State, Event>` from `com.jarvis.chat.core.viewmodel`.
Generic order is exactly that: UiState second, State third, Event fourth.

```kotlin
internal class ChatViewModel(
    private val sendMessage: SendMessageUseCase,
) : UdfBaseViewModel<ChatAction, ChatUiModel, ChatState, ChatEvent>(
    initialState = ChatState(),
    uiMapper = ChatUiMapper(),
) {
    override fun onAction(action: ChatAction) { ... }
}
```

- Data flows one way: `UI -> Action -> ViewModel -> updateState -> State -> UiMapper -> UiModel -> UI`.
- One-off signals go through `Event`: `postEvent(...)`.
- State update only via `updateState { copy(...) }`. Never `_state.value = ...`.
- `*Action` is a `sealed interface` with nested `Ui` and `Internal` sub-interfaces.
- `*State` is an `internal data class` with default values for every field.

# Mappers

- data -> domain: top-level extension `internal fun XxxResponseModel.toXxxModel(): XxxModel` in `data/mapper/`.
- State -> UiModel: class `internal class XxxUiMapper : UiMapper<XxxState, XxxUiModel>` in `presentation/mapper/`.
- Inline mapping inside a repository or ViewModel is forbidden.

# Kotlin rules

- `internal` by default. `public` only for real cross-module API.
- Lambda parameters are always named, even single ones: `messages.map { message -> message.id }`. Never `it`.
- No `!!`. Handle nullability explicitly.
- No `Any` as a type. Use generics.
- No magic numbers. Extract a `private const val`.
- Explicit parameter and return types on functions.
- Full imports, never `*`.
- Secrets come from `AppConfig` through Koin DI. Never hardcode a key or a token.
- Do not write comments or KDoc unless explicitly asked.

# Reference example

```kotlin
package com.jarvis.chat.feature.ai.data.mapper

import com.jarvis.chat.feature.ai.data.model.ChatCompletionResponseModel
import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor

internal fun ChatCompletionResponseModel.toChatMessageModel(): ChatMessageModel =
    ChatMessageModel(
        author = MessageAuthor.ASSISTANT,
        text = choices.firstOrNull()?.message?.content.orEmpty(),
    )
```

# Forbidden, concrete

- `DeepSeekMessageDto`, package `data/remote/dto/`
- `class ChatUiState`
- `_state.value = state.copy(...)`
- mapping a response model to a domain model inside `ChatRepositoryImpl`
- `apiKey = "sk-..."`, `token!!`, `fun handle(payload: Any)`
