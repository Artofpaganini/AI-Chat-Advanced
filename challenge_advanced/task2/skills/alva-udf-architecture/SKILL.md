---
name: alva-udf-architecture
description: "UDF/MVI architecture pattern details for Alva (KMP/CMP) — Action / UiState / Event / State for shared ViewModels consumed from Android & iOS"
---

# UDF (Unidirectional Data Flow) Architecture — Alva

## Core Principles

### ViewModel Base
- Use `UdfBaseViewModel<Action, UiState, Event, State>` from Alva's shared `:core:viewmodel` module.
- Do not extend plain `ViewModel` for UDF screens.

### State Management
- **State:** single `State` (data class) holds all screen data.
- Map to `UiState` via a mapper.
- Update ONLY with `updateState { copy(...) }`.
- Keep State immutable (all `val` properties).

### Actions
- Sealed interface `Action` with nested:
  - `User` — user events (clicks, input)
  - `Internal` — `Initialize`, `Launch`, `Cancel`, `HandleEvent`, lifecycle triggers, observers' callbacks

### Events (one-off UI effects)
- In Alva the one-off UI effect is named **`Event`** (not SideEffect).
- Use `postEvent(event)` in ViewModel.
- Consume via `getEvent()` / `collectEvent()` in UI.
- Call `handleEvent()` after the UI finished processing the event — otherwise the queue stalls and re-emits the same event.
- Typical payloads: navigation commands, toasts/snackbars, alerts, analytics triggers.

### Scopes
- Use `withScope { }` or `flow.withScope()` for coroutine work inside the ViewModel.
- Prefer `udfDispatchers` (`map` for State → UiState mapping, `work` for business logic) instead of resolving `Dispatchers` directly.
- Cancel all jobs on ViewModel clear (handled by `viewModelScope` — never launch in another scope).

## Data Flow

```
User Input → Action → ViewModel → updateState → State → Mapper → UiState → UI
                           ↓
                     postEvent → UI consumes one-off → handleEvent()
```

The loop is strictly unidirectional: UI never writes to State directly, and the ViewModel exposes only `UiState` (derived) + `Event` streams — never the internal `State`.

## Testing seams
- Assertions target the internal `State` (available as `viewModel.state` delegate) and the `Event` stream — never the mapped `UiState` (that is covered by a separate mapper test).
