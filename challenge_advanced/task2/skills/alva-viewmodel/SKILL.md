---
name: alva-viewmodel
description: "Use when working with core:viewmodel in Alva (KMP/CMP) — creating/extending UdfBaseViewModel, wiring State/UiState mapping (mapper / mapHolder / ContentHolder / ContentSource / ContentConsumer), posting/handling Events, or creating ViewModels via udfViewModel in Compose Multiplatform screens consumed from Android & iOS"
---

# core:viewmodel — UdfBaseViewModel Reference (Alva)

Module path: `core/viewmodel` (KMP common module). Contains the shared UDF ViewModel framework consumed by all Alva features from both Android and iOS. Code is platform-agnostic; every screen ViewModel lives in `commonMain` of the feature's `impl` module.

## 1. Module Surface

### Hosts / abstractions
- `UdfViewModel<Action, UiState, Event>` — abstract ViewModel base. Public API: `onAction(action)`, `collectUiState()`, `collectEvent()`, `getUiState()`, `getEvent()`.
- `UdfBaseViewModel<Action : Any, UiState, Event, State : Any>` — concrete base. Extend this for every UDF screen. Two constructors:
  - **Primary:** `initialState: () -> State`, `mapper: (State) -> UiState`, `dispatchers: UdfDispatchers`.
  - **Secondary:** same, but `mapHolder: (State) -> UiMapper<State, UiState>` instead of `mapper`.

### Creation extension
- **Compose Multiplatform:** `udfViewModel(viewModelKey = SomeViewModel::class, viewModelFactory = …)` — lazy, scoped to the current `ViewModelStoreOwner`. For variants use `customKey` (e.g. pager pages with repeated ViewModels).

### Mapping helpers
- `UiMapper<State, UiState>` — functional interface, `invoke(state) -> UiState`.
- `contentHolder(initial) { block }` → two-way holder (State + UiState). `.value` = current State, `.uiValue` = current UiState, `.state` / `.uiState` = ComposeState streams. Update via `updateTo(newValue)` or `updateTo { … }`.
- `contentSource(initial)` → one-way source of State (no UiState projection).
- `contentConsumer(producer) { block }` → listens to another `ComposeState` and derives UiState only.

### Observation
- Compose: `val uiState by viewModel.collectUiState()`.
- Events: `LaunchedEffect(Unit) { viewModel.getEvent().collect { event -> … ; viewModel.handleEvent() } }`.

### Coroutines / scope
- `withScope(coroutineDispatcher, onError) { … }` — wraps `viewModelScope.launchJob`. Default dispatcher = `dispatchers.work`.
- `Flow<T>.withScope(dispatcher, onError)` — `launchInJob` in `viewModelScope + dispatcher`.
- `UdfDispatchers { map, work }` — `map` for State → UiState, `work` for business logic. Create with `udfDispatchers(map, work)`. In tests substitute both with the `TestDispatcher`.

### Deferred / pending Events
- `postOnReturnEvent(event, condition)` — store event, replay on re-subscribe when `condition() == true`. Used for flows that must replay after the user returns to the screen.
- `postPendingEvent` / `handleEvent` — lifecycle of the pending queue.

## 2. Required Naming

| Concept | Suffix (REQUIRED) | Wrong (FORBIDDEN) |
|---|---|---|
| Action hierarchy | `SomeAction` | `SomeIntent`, `SomeMessage` |
| UI state | `SomeUiState` | `SomeUiModel`, `SomeModel` |
| One-off event | `SomeEvent` | `SomeSideEffect`, `SomeAction` |
| Internal state | `SomeState` | `SomeStateModel`, `SomeModel` |
| ViewModel | `SomeViewModel` | — |

`Action` must be a `sealed interface` with nested `User : SomeAction` and `Internal : SomeAction` hierarchies. `User` = UI-triggered. `Internal` = system / lifecycle / `HandleEvent` / `LaunchX` / `Cancel`.

## 3. Best Practices

### State
- `State` is a **data class only** (never sealed). Store **all** intermediate data inside State — no private properties next to the ViewModel.
- Load remote/feature configs in `initialState = { … }` once, and keep the resolved values inside State. Do NOT call use cases from inside the mapper.
- Update only via `updateState { copy(...) }`.
- Read latest State via the `state` delegate property (available in ViewModel and tests).

### Mapping
- **Simple screens:** use the primary constructor with `mapper = SomeState::toSomeUiState`. Keep the mapper pure and cheap — it runs on every State change on `dispatchers.map`.
- **Heavy screens:** use the secondary constructor with `mapHolder = { state -> SomeUiStateMapper(state, stringProvider, …) }`. Inside the mapper:
  - Declare `contentHolder` / `contentSource` / `contentConsumer` as `by`-delegated `val`s.
  - In `invoke(state)` call `holder.updateTo { state.xxx }` for every holder. Remapping happens only when the underlying piece actually changed.

### Events
- Post with `postEvent(SomeEvent)`. On UI collect once; after consumption call `viewModel.handleEvent()` — otherwise the queue stalls and re-emits the same event.
- For deferred flows (e.g. action-on-return after a child screen): `postOnReturnEvent(event = RecallXOnReturn(data), condition = { … })`.
- Follow-through actions come back as `SomeAction.Internal.HandleEvent` — handle them via a `handleEvent()` branch.

### Dispatchers
- Inject `UdfDispatchers` via Koin. Production: `map = Dispatchers.Default`, `work = Dispatchers.IO` (or project-provided KMP equivalents).
- Tests: use the test harness to substitute both fields with the single `TestDispatcher`.

## 4. Anti-Patterns (FORBIDDEN)

- ❌ Using `UiModel` / `Event` / `Intent` / `Message` / `StateModel` as generic names instead of the canonical suffixes (note: `Event` IS the canonical suffix for one-off effects in Alva, but it must be used ONLY for the one-off event generic — not for Action or State).
- ❌ Running use cases inside `mapper = { state -> … }`. They must be called in `initialState` or in `onAction` handlers and stored in State.
- ❌ Declaring private `var` / `val` properties alongside the ViewModel to keep screen data. Everything screen-related goes into State.
- ❌ Removing `super.onAction(action)` in your ViewModel's `onAction` override — breaks action logging / action pipeline.
- ❌ Calling `handleEvent()` on the UI without actually handling the event first (breaks ACID semantics — the queue gets stuck).
- ❌ Exposing internal `State` outside the ViewModel (consumers must only see `UiState` and `Event`).
- ❌ Launching coroutines in a scope other than `viewModelScope` (via `withScope` / `Flow.withScope`) — breaks cancellation on clear.

## 5. Minimal Skeleton

```kotlin
// commonMain in feature/<name>/impl/presentation/viewmodel
internal class SomeViewModel(
    private val loadSomethingUseCase: LoadSomethingUseCase,
    stringProvider: StringProvider,
    dispatchers: UdfDispatchers,
) : UdfBaseViewModel<SomeAction, SomeUiState, SomeEvent, SomeState>(
    initialState = {
        SomeState(
            isLoading = true,
            items = emptyList(),
        )
    },
    mapper = SomeStateToUiStateMapper(stringProvider),
    dispatchers = dispatchers,
) {

    override fun onAction(action: SomeAction) {
        super.onAction(action)
        when (action) {
            is SomeAction.User.OnLoadClick -> handleLoadClick()
            is SomeAction.Internal.HandleEvent -> handleEvent()
        }
    }

    private fun handleLoadClick() {
        withScope {
            val items = loadSomethingUseCase.invoke()
            updateState { copy(isLoading = false, items = items) }
        }
    }
}
```

Consumed from a Compose Multiplatform screen:

```kotlin
@Composable
internal fun SomeScreen(
    viewModel: UdfViewModel<SomeAction, SomeUiState, SomeEvent> = udfViewModel(
        viewModelKey = SomeViewModel::class,
        viewModelFactory = featureDi.getViewModelFactory(),
    ),
) {
    val uiState by viewModel.collectUiState()
    LaunchedEffect(Unit) {
        viewModel.getEvent().collect { event ->
            // handle navigation / toast / dialog based on event
            viewModel.handleEvent()
        }
    }
    // render uiState ...
}
```

## 6. Related Skills
- `alva-udf-architecture` — UDF pattern basics.
- `alva-project-context` — module packaging rules (where `viewmodel/`, `state/`, `action/`, `event/`, `uistate/`, `mapper/` live), visibility rule, Koin DI setup.
