---
name: xbet-reference-modules
description: "Reference modules for Mobile_Android_OnexBet architecture patterns"
---

# Reference Modules

Best practice modules to use as architectural references.

## Core Modules

### :core:viewmodel
- `UdfBaseViewModel<Action, UiState, SideEffect, State>` - base for UDF ViewModels
- Extensions: `updateState`, `postSideEffect`, `handleSideEffect`

### :core:test
- `TestCoroutinesInitializer` + `TestCoroutinesInitializerExtension` - coroutine testing
- `FlowTestResultHandler` (`flow.handleTest(scope)`) - Flow assertions
  - `assertValues(...)`, `assertValue(...)`, `assertNoErrors()`, `assertErrorType(...)`
  - Call `finish()` when done

### :ui_core
- `viewModelScope.launchJob(catchBlock, context)` - safe coroutine launch
- `observeWithLifecycle` / `observeWithLifecycleLatest` - lifecycle-aware collection

## Feature Modules

### :feature/top/dynamic
Large screens with delegates, content adapters. Multiple content types with delegate-based architecture.

### :feature:auth:login
Auth flows, validation, multi-step processes. Use cases, scenarios, state management.

### :sportgame:dashboard & :sportgame:advanced
Real-time streams, complex state. Multiple streams collected via `withScope`/`launchInJob`.

### :uikit/uikit_sport
Compose UI components, design system.

## Usage
Mirror patterns from reference modules. Do not change core utilities - use as-is.
