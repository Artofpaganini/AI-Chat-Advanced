# Примеры кода — alva (KMM + Compose Multiplatform)

Стек: KMP · Koin · Compose Navigation 3 · UDF со **Event** · `Alva`-префикс · Kotlin DSL + convention-plugins ·
`composeResources/` · один shared Compose = Android+iOS. Общие правила — глобальный `~/.claude/CLAUDE.md`.
Детали — skill `alva-project-context`/`alva-udf-architecture`/`alva-viewmodel`/`navigation-3`/`compose-principles`.

## КАК НАДО (хорошо)
```kotlin
// 1) StateFlow атомарно, именованная лямбда
_state.update { current -> current.copy(isLoading = false, child = child) }

// 2) сетевая модель — суффикс, @Serializable, internal (НЕ Dto)
@Serializable
internal data class ChildResponseModel(val id: String, val name: String)

// 3) data→domain маппер — extension в data/mapper/ (один файл на модель)
internal fun ChildResponseModel.toChildModel(): ChildModel = ChildModel(id = id, name = name)

// 4) State→UiModel — класс UiMapper в presentation/mapper/
internal class ChildUiMapper : UiMapper<ChildState, ChildUiModel> {
    override fun invoke(state: ChildState): ChildUiModel = ChildUiModel(title = state.name)
}

// 5) Action — sealed Ui/Internal
internal sealed interface ChildAction {
    sealed interface Ui : ChildAction { data class Rename(val name: String) : Ui }
    sealed interface Internal : ChildAction { data object Load : Internal }
}

// 6) VM — UdfBaseViewModel<Action, UiModel, State, Event>, one-off = Event, Koin (viewModelOf/constructor)
internal class ChildViewModel(
    private val loadChild: LoadChildUseCase,
    dispatchers: DispatchersProvider,
) : UdfBaseViewModel<ChildAction, ChildUiModel, ChildState, ChildEvent>(...) {
    private fun onSaved() { postEvent(ChildEvent.NavigateBack) }
}

// 7) DI — Koin
val childModule = module { viewModelOf(::ChildViewModel); factoryOf(::LoadChildUseCase) }

// 8) навигация — Compose Navigation 3; UI — префикс Alva, ОДИН shared Compose на обе платформы
navigator.navigate(ChildRoute(childId)); AlvaButton(onClick = { … }) { AlvaText("Save") }

// 9) expect/actual — платформа в своём source set, в commonMain платформенного кода нет
expect fun createHttpEngine(): HttpClientEngine   // androidMain: OkHttp; iosMain: Darwin
```

## КАК НЕЛЬЗЯ (плохо)
```kotlin
class ChildDto(...)                        // ❌ «Dto» → *ResponseModel/*DataModel/*Model
data class ChildUiState(...)               // ❌ класс *UiState → *UiModel
_state.value = _state.value.copy(...)      // ❌ → _state.update { s -> s.copy(...) }
postSideEffect(ChildSideEffect.Back)       // ❌ в alva one-off = Event: postEvent(...)
// два разных UI под Android и iOS          // ❌ обычный экран = ОДИН shared Compose (@AndroidUiDev), не плодить @IosUiDev
val n = child!!.name                       // ❌ !! → обработать null
android.util.Log в commonMain              // ❌ платформенное в commonMain → expect/actual (или Napier)
items.map { it.id }                        // ❌ неявный it → items.map { item -> item.id }
class ChildMapper { fun mapToUi()=… }      // ❌ маппер-класс → extension + UiMapper
```

## Шаблон типичного файла (alva feature)
```kotlin
package com.alva.feature.child.presentation.mapper

import com.alva.core.viewmodel.mapping.UiMapper
import com.alva.feature.child.presentation.model.ChildState
import com.alva.feature.child.presentation.model.ChildUiModel

internal class ChildUiMapper : UiMapper<ChildState, ChildUiModel> {
    override fun invoke(state: ChildState): ChildUiModel =
        ChildUiModel(title = state.name, isLoading = state.isLoading)
}
```
Порядок: `package` → полные импорты → одна сущность/файл → `internal` по умолчанию.
