# Примеры кода - base (кросс-платформа: Android / KMM+CMP / Backend)

Общие правила - глобальный `~/.claude/CLAUDE.md`. Ниже - моменты по коду **под каждое направление**; конкретное
направление выбирается на создании задачи. Стек 2026 - см. глобальный CLAUDE.md «Стек по платформам».

## Направление: Android (нативный)
Kotlin 2.x · Compose+Material3 · Hilt/Koin · Coroutines/Flow · ViewModel+Lifecycle · Retrofit/Ktor · Room · MVI/UDF.
```kotlin
// ✅ хорошо
@HiltViewModel class ProfileViewModel @Inject constructor(private val load: LoadProfileUseCase) : ViewModel() {
    private val _state = MutableStateFlow(ProfileUiState())
    val state = _state.asStateFlow()
    fun onLoad() = viewModelScope.launch { _state.update { s -> s.copy(items = load()) } }   // атомарно
}
sealed interface ProfileIntent { data object Load : ProfileIntent }                          // sealed intents
```
```kotlin
// ❌ плохо
GlobalScope.launch { ... }                 // ❌ утечка -> viewModelScope/structured concurrency
_state.value = _state.value.copy(...)      // ❌ -> _state.update { … }
findViewById / AsyncTask                   // ❌ в Compose-экране; устаревшее
val x = user!!.name                        // ❌ !! -> обработать null
```

## Направление: KMM + Compose Multiplatform
KMP · Compose MP (iOS stable) · Ktor+serialization · Koin · SQLDelight/Room-KMP · Nav3/Decompose · UDF.
```kotlin
// ✅ хорошо - expect/actual, Koin, суффиксы моделей, один shared Compose
expect fun createHttpEngine(): HttpClientEngine        // androidMain: OkHttp; iosMain: Darwin
@Serializable internal data class UserResponseModel(val id: String, val name: String)
internal fun UserResponseModel.toUserModel(): UserModel = UserModel(id, name)
```
```kotlin
// ❌ плохо
class UserDto(...)                         // ❌ «Dto» -> *ResponseModel/*Model
android.util.Log(...) в commonMain         // ❌ платформенное в commonMain -> expect/actual / Napier
data class UserUiState(...)                // ❌ класс *UiState -> *UiModel
```

## Направление: Backend (Kotlin / Java)
Kotlin 2.x/Java 21 · Spring Boot 3 / Ktor server · Coroutines · Exposed/JPA/jOOQ · PostgreSQL · Flyway · Testcontainers.
```kotlin
// ✅ хорошо - constructor injection, request/response модели, структурная ошибка, без утечки стека
@Service class OrderService(private val repo: OrderRepository) {
    suspend fun place(req: PlaceOrderRequestModel): Result<OrderResponseModel> = runCatching { ... }
}
@Serializable data class PlaceOrderRequestModel(val userId: Long, val items: List<Long>)     // валидируется
```
```kotlin
// ❌ плохо
return orderEntity                         // ❌ отдавать JPA-entity наружу -> маппить в *ResponseModel
catch (e: Exception) { throw e }           // ❌ прокидывать stacktrace клиенту -> структурная ошибка + код
repo.findAll().forEach { it.items }        // ❌ N+1 запрос -> join/batch
runBlocking { ... } в suspend-контексте    // ❌ блокировка -> suspend/withContext
val key = "secret123"                      // ❌ секрет в коде -> env/Vault/config
```

## Шаблон (generic, любое направление)
```kotlin
package com.example.feature.profile.data.mapper   // package первым

import com.example.feature.profile.data.model.ProfileResponseModel   // полные импорты, без *
import com.example.feature.profile.domain.model.ProfileModel

internal fun ProfileResponseModel.toProfileModel(): ProfileModel =   // одна сущность/файл, internal по умолчанию
    ProfileModel(id = id, name = name)
```
