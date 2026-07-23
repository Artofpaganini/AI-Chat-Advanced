# Примеры кода - xbet (Mobile_Android_OnexBet + twin xbet1)

Стек: Android · Dagger 2 · Cicerone (`XPlatformRouter`, классы не менять) · UDF со **SideEffect** · `Ds`-префикс ·
Groovy Gradle · `strings.xml`. Общие правила - глобальный `~/.claude/CLAUDE.md`. Детали - skill `xbet-project-context`/`xbet-udf-architecture`/`xbet-viewmodel`/`xbet-navigation`/`xbet-testing`.

## КАК НАДО (хорошо)
```kotlin
// 1) StateFlow атомарно, именованная лямбда
_state.update { current -> current.copy(isLoading = false, coefficient = coef) }

// 2) сетевая модель - суффикс, @Serializable, internal (НЕ Dto)
@Serializable
internal data class BetRequestModel(val eventId: Long, val amount: Double)

// 3) data->domain маппер - extension в data/mapper/
internal fun BetResponseModel.toBetModel(): BetModel = BetModel(id = id, status = status)

// 4) State->UiModel - класс UiMapper в presentation/mapper/
internal class BetUiMapper : UiMapper<BetState, BetUiModel> {
    override fun invoke(state: BetState): BetUiModel = BetUiModel(title = state.title)
}

// 5) Action - sealed Ui/Internal
internal sealed interface BetAction {
    sealed interface Ui : BetAction { data class PlaceBet(val amount: Double) : Ui }
    sealed interface Internal : BetAction { data object Load : Internal }
}

// 6) VM - UdfBaseViewModel<Action, UiModel, State, SideEffect>, one-off = SideEffect, Dagger-фабрика
internal class BetViewModel @AssistedInject constructor(
    private val placeBet: PlaceBetUseCase,
    private val router: XPlatformRouter,
) : UdfBaseViewModel<BetAction, BetUiModel, BetState, BetSideEffect>(...) {
    private fun onPlaced() { postSideEffect(BetSideEffect.ShowSuccess) }
}

// 7) навигация - Cicerone XPlatformRouter (классы Cicerone НЕ трогать)
router { navigate(BetResultScreen(betId)) }

// 8) тест (opt-in) - FlowTestResultHandler + verifyRouter
val handler = viewModel.getSideEffect().handleTest(this)
viewModel.onAction(BetAction.Ui.PlaceBet(100.0))
handler.finish(); verifyRouter(router) { navigate(any()) }
```

## КАК НЕЛЬЗЯ (плохо)
```kotlin
class BetDto(...)                          // ❌ «Dto» -> *RequestModel/*ResponseModel/*DataModel
data class BetUiState(...)                 // ❌ класс *UiState -> *UiModel
_state.value = _state.value.copy(...)      // ❌ -> _state.update { s -> s.copy(...) }
postEvent(BetEvent.Done)                   // ❌ в xbet one-off = SideEffect: postSideEffect(...)
class BetVM { val vm by koinInject() }     // ❌ VM через Dagger ViewModelFactory, НЕ koinInject/viewModelOf
// правка классов Cicerone Router          // ❌ Cicerone НЕ менять - только XPlatformRouter DSL
val x = coef!!.value                       // ❌ !! -> обработать null
items.map { it.id }                        // ❌ неявный it -> items.map { item -> item.id }
repo: BetModel(r.id, r.status)             // ❌ инлайн-маппинг -> toBetModel() в data/mapper/
// считаем коэффициент                     // ❌ комментарий без просьбы
```

## Шаблон типичного файла (xbet feature)
```kotlin
package org.xplatform.feature.bet.data.mapper

import org.xplatform.feature.bet.data.model.BetResponseModel
import org.xplatform.feature.bet.domain.model.BetModel

internal fun BetResponseModel.toBetModel(): BetModel =
    BetModel(id = id, status = status, coefficient = coefficient)
```
Порядок: `package` -> полные импорты -> одна сущность/файл -> `internal` по умолчанию.
