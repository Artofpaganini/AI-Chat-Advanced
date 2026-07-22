---
name: xbet-viewmodel
description: "Use when working with core:viewmodel in Mobile_Android_OnexBet — creating/extending UdfBaseViewModel, UdfBaseDelegate, wiring State/UiState mapping (mapper/mapHolder/ContentHolder/ContentSource/ContentConsumer), posting/handling SideEffects, observing delegates, or creating ViewModels via udfViewModel in Compose/Fragment"
---

# core:viewmodel — UdfBaseViewModel / UdfBaseDelegate Reference

Module path: `core/viewmodel`. Package root: `org.xplatform.core.viewmodel.*`.

## 1. Module Surface

### Hosts / abstractions
- `UdfViewModel<Action, UiState, SideEffect>` — abstract `ViewModel`, implements `UdfContentProvider`. Public API: `onAction(action)`, `collectUiState()`, `collectSideEffect()`, `observeContent(...)`, `getUiState()`, `getSideEffect()`.
- `UdfBaseViewModel<Action : Any, UiState, SideEffect, State : Any>` — concrete base. Extend this for every UDF screen. Two constructors:
  - **Primary:** `initialState: () -> State`, `mapper: (State) -> UiState`, `dispatchers: UdfDispatchers`.
  - **Secondary:** same, but `mapHolder: (State) -> UiMapper<State, UiState>` instead of `mapper`.
- `UdfDelegate<DelegateAction, DelegateState, DelegateSideEffect>` — interface contract for delegates.
- `UdfBaseDelegate<DelegateAction : Any, DelegateState, DelegateSideEffect>(initialState)` — base for delegate implementations. `onAction` is **suspend**. No `viewModelScope`, no `SavedStateHandle` inside delegates (enforced by detekt).

### Creation extensions
- **Compose:** `udfViewModel(viewModelKey = SomeViewModel::class, viewModelFactory = daggerComponent.getViewModelFactory())` or with `customKey`.
- **Fragment:** `by udfViewModel(viewModelKey = SomeViewModel::class, viewModelFactory = { viewModelFactory })` or typed generics form.
- `Fragment.udfViewModel(savedStateViewModelFactory = …)` and `by viewModels<…>` are **deprecated / forbidden** — breaks UDF encapsulation.

### Factories
- `ViewModelFactory<VM, XPlatformRouter>` — contract with `create(router): VM`.
- `AssistedViewModelFactory`, `SavedStateRouterViewModelFactory` — assisted injection with router.
- `ServiceViewModelProvider` — creating ViewModels outside composition.

### Mapping helpers
- `UiMapper<State, UiState>` — functional interface, `invoke(state) -> UiState`.
- `contentHolder(initial) { block }` → two-way holder (State + UiState).
- `contentSource(initial)` → one-way source of State.
- `contentConsumer(producer) { block }` → listens ComposeState, maps to UiState only.
- Use `updateTo(newValue)` / `updateTo { … }` on holders. Use `.value` for State, `.uiValue` for UiState, `.state` / `.uiState` for ComposeState streams.

### Observation
- Compose: `val uiState by viewModel.collectUiState()`; `LaunchedEffect(Unit) { viewModel.getSideEffect().collect { … ; viewModel.handleSideEffect() } }`.
- Fragment: `viewModel.observeContent(fragment, uiState = { … }, sideEffect = { … })`.

### Coroutines / scope
- `withScope(coroutineDispatcher, onError) { … }` — wraps `viewModelScope.launchJob`. Default dispatcher = `dispatchers.work`.
- `Flow<T>.withScope(dispatcher, onError)` — `launchInJob` in `viewModelScope + dispatcher`.
- `UdfDispatchers { map, work }` — `map` for State→UiState, `work` for business logic. Create with `udfDispatchers(map, work)`.

### Delegate API (inside ViewModel)
- `delegate.observeDelegate(onState, onSideEffect, onError, onDeferActionResult)` → returns `Job`. Save it and cancel on screen leave. `onSideEffect` takes two lambdas: `send` (wrap delegate effect into ViewModel effect) and `handle` (action to mark delegate effect as handled).
- `delegate.delegateActionInScope(action)` / `delegateActionsInScope(vararg actions)` — dispatch delegate actions in `viewModelScope`.

### Actions (deferred / pending)
- `postOnReturnSideEffect(effect, condition)` — store effect, replay on re-subscribe when `condition() == true`. Used for actions that need replay after auth return.
- `postPendingSideEffect` / `handleSideEffect` — lifecycle of the pending queue.

## 2. Required Naming

| Concept | Suffix (REQUIRED) | Wrong (FORBIDDEN) |
|---|---|---|
| Action hierarchy | `SomeAction` | `SomeEvent`, `SomeIntent` |
| UI state | `SomeUiState` | `SomeUiModel`, `SomeModel` |
| Side effect | `SomeSideEffect` | `SomeEvent`, `SomeAction` |
| Internal state | `SomeState` | `SomeStateModel`, `SomeModel` |
| ViewModel | `SomeViewModel` | — |
| Delegate contract | `SomeDelegate` | — |
| Delegate impl | `SomeDelegateImpl` | — |

`Action` must be a `sealed interface` with nested `User : SomeAction` and `Internal : SomeAction` hierarchies. `User` = UI-triggered. `Internal` = system / lifecycle / `HandleSideEffect` / `LaunchX` / `Cancel`.

## 3. Best Practices

### State
- `State` is a **data class only** (never sealed). Store **all** intermediate data inside State — no private properties next to the ViewModel.
- Load remote/feature configs in `initialState = { … }` once, and keep the resolved values inside State. Do NOT call use cases from inside the mapper.
- Update only via `updateState { copy(...) }`.
- Read latest State via the `state` delegate property (available in ViewModel and tests).

### Mapping
- **Simple screens:** use primary constructor with `mapper = SomeState::toSomeUiState`. Keep the mapper pure and cheap — it runs on every State change on `dispatchers.map`.
- **Heavy screens:** use secondary constructor with `mapHolder = { state -> SomeUiStateMapper(state, resourceManager, …) }`. Inside the mapper:
  - Declare `contentHolder` / `contentSource` / `contentConsumer` as `by`-delegated `val`s.
  - In `invoke(state)` call `holder.updateTo { state.xxx }` for every holder. Remapping happens only when the underlying piece actually changed.
- Reference mappers in-tree: `DynamicTopUiStateMapper`, `GameAdvancedUiStateMapper`.

### Side effects
- Post with `postSideEffect(SomeSideEffect)`. On UI collect once; after consumption call `viewModel.handleSideEffect()` — otherwise the queue stalls and re-emits.
- For deferred flows (e.g. auth-gated actions): `postOnReturnSideEffect(effect = RecallXWhenReturn(data), condition = getAuthorizationStateUseCase::invoke)`.
- Follow-through actions come back as `SomeAction.Internal.HandleSideEffect` — handle them via a `handleSideEffect()` branch.

### Delegates
- Each delegate lives in its own api/impl split: interface `SomeDelegate : UdfDelegate<DelegateAction, DelegateState, DelegateSideEffect>` in `api`, `SomeDelegateImpl : UdfBaseDelegate<…>` in `impl`, Dagger `@Binds @Reusable`.
- If the delegate is feature-local, `SomeDelegateAction/State/SideEffect` may be nested inside the ViewModel's sealed hierarchies.
- Always store the `observeDelegate(...)` job and cancel it when the screen is destroyed (activity recreation → otherwise leaks).
- Forward UI delegate events via a wrapper action: `User.SportItem(val delegateAction: SportDelegateAction.User)`.

### Dispatchers
- Inject `UdfDispatchers` through Dagger. Production: `map = Dispatchers.Default`, `work = Dispatchers.IO` (or project-provided).
- Tests: use `TestCoroutinesInitializer` + `testDispatcher` for both fields.

## 4. Anti-Patterns (FORBIDDEN)

- ❌ Creating a ViewModel with `by viewModels<UdfBaseViewModel<A, U, S, State>>` — exposes State to UI and breaks UDF encapsulation. Use `udfViewModel(...)` only.
- ❌ Using `UiModel`/`Event`/`Intent`/`StateModel` as generic names instead of the canonical suffixes.
- ❌ Running use cases inside `mapper = { state -> … }`. They must be called in `initialState` or in `onAction` handlers and stored in State.
- ❌ Declaring private `var` / `val` properties alongside the ViewModel to keep screen data. Everything screen-related goes into State.
- ❌ Inside delegates: referencing `SavedStateHandle` or spawning your own `CoroutineScope`. Delegates are action-in, suspend-processed. Reach out to the lead if you hit a case that seems to need it.
- ❌ Removing `super.onAction(action)` in your ViewModel's `onAction` override — breaks action logging and `actionManager`.
- ❌ Calling `handleSideEffect()` on the UI without actually handling the effect first (breaks ACID semantics, queue gets stuck).

## 5. Minimal Skeleton

```kotlin
// ViewModel
internal class SomeViewModel @Inject constructor(
    private val router: XPlatformRouter,
    private val useCase: SomeUseCase,
    private val someDelegate: SomeDelegate,
    resourceManager: ResourceManager,
    dispatchers: UdfDispatchers,
) : UdfBaseViewModel<SomeAction, SomeUiState, SomeSideEffect, SomeState>(
    initialState = {
        SomeState(
            isLoading = true,
            items = emptyList(),
        )
    },
    mapper = SomeStateToUiStateMapper(resourceManager),
    dispatchers = dispatchers,
) {

    private var delegateJob: Job? = null

    init {
        observeSomeDelegate()
    }

    override fun onAction(action: SomeAction) {
        super.onAction(action)
        when (action) {
            is SomeAction.User.OnLoadClick -> handleLoadClick()
            is SomeAction.Internal.HandleSideEffect -> handleSideEffect()
            is SomeAction.User.SportItem -> someDelegate.delegateActionInScope(action.delegateAction)
        }
    }

    private fun handleLoadClick() {
        withScope {
            val items = useCase.invoke()
            updateState { copy(isLoading = false, items = items) }
        }
    }

    private fun observeSomeDelegate() {
        delegateJob = someDelegate.observeDelegate(
            onState = { updateState { copy(items = list) } },
            onSideEffect = { send, handle ->
                send { delegateEffect -> SomeSideEffect.Wrap(delegateEffect) }
                handle { SomeDelegateAction.Internal.HandleSideEffect }
            },
        )
    }
}
```

## 6. Related Skills
- `xbet-udf-architecture` — UDF pattern basics.
- `xbet-testing` — testing ViewModels / delegates / flows.
- `xbet-navigation` — using `XPlatformRouter` from ViewModels.
- `xbet-project-context` — module packaging rules (where `viewmodel/`, `state/`, `action/`, `sideeffect/`, `uistate/`, `mapper/`, `delegate/` live).
