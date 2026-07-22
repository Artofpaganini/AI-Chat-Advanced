---
name: xbet-udf-architecture
description: "UDF/MVI architecture pattern details for Mobile_Android_OnexBet"
---

# UDF (Unidirectional Data Flow) Architecture

## Core Principles

### ViewModel Base
- Use `UdfBaseViewModel<Action, UiState, SideEffect, State>` from `:core:viewmodel`
- Do not extend plain `ViewModel` for UDF screens
- Use `BaseViewModel` from ui_core only when NOT using UDF

### State Management
- **State**: Single `State` (data class) holds all screen data
- Map to `UiState` via a mapper
- Update ONLY with `updateState { copy(...) }`
- Keep State immutable (all `val` properties)

### Actions
- Sealed interface `Action` with nested:
  - `User` - user events (clicks, input)
  - `Internal` - Initialize, Launch, Cancel, HandleSideEffect
- User actions often wrap delegate actions:
  ```kotlin
  data class SportItem(val delegateAction: SportDelegateAction.User)
  ```

### Side Effects
- One-off UI events: navigation, toasts, dialogs
- Use `postSideEffect(effect)` in ViewModel
- Consume via `getSideEffect()` in UI
- Call `handleSideEffect()` after handling

### Delegates
- Use `UdfDelegate<DelegateAction, DelegateState, DelegateEffect>`
- Subscribe with `observeDelegate(onState = ..., onSideEffect = ...)`
- Forward actions: `delegateActionInScope(action)`
- Cancel jobs when leaving screen

### Scopes
- Use `withScope { }` or `flow.withScope()` for coroutine work
- Prefer `udfDispatchers` for map/work
- Cancel all jobs on ViewModel clear

## Data Flow

```
User Input → Action → ViewModel → updateState → State → Mapper → UiState → UI
                           ↓
                    postSideEffect → UI handles one-off events
```
