---
name: xbet-navigation
description: "Use when working with core:navigation in Mobile_Android_OnexBet — calling XPlatformRouter DSL (router { navigate / replace / newRoot / show / dismiss / openLogin / openRegistration / doAction / doSuspendAction / backTo / exit / finishRoot / newChain / startChildChain }), configuring commands with withConfig { isAuthRequire / forDialog / forAuthorization }, wiring XPlatformRouterProvider, or verifying navigation in tests"
---

# core:navigation — XPlatformRouter Reference

Module path: `core/navigation`. Package root: `org.xplatform.core.navigation.*`.

`XPlatformRouter` is an internal wrapper over Cicerone (`BaseRouter`) that adds three capabilities the library lacks:
1. **DSL (`router { … }` + `withConfig { … }`)** — single, predictable way to build commands.
2. **Authorization-aware routing** — `isAuthRequire = true` auto-intercepts via `AuthorizationInterceptor`, replays the original command as `pendingCommand` after login.
3. **Virtual navigation stack** — `NavigationStackHolder` keeps the source of truth about what's open (including dialogs), independent of FragmentManager.

## 1. Module Surface

### Core entry points
- `XPlatformRouter : BaseRouter()` — one per container (Activity / TabContainer / Aggregator).
  - `operator fun invoke(block: XPlatflormRouterCommandConfigurator.() -> Unit)` → enables `router { … }`.
  - `@RouterConfigurationApi` callbacks: `setAuthorizeCallback`, `setAuthScreenCallback`, `setSuspendActionCallback`. **Configure only in `app` module** (`XPlatformRouterProviderImpl`). Never call from feature modules.
- `XPlatformRouterStub` — safe no-op fallback returned by `RouterHolder` when no router is attached.

### Configurator DSL
`XPlatflormRouterCommandConfigurator` — available inside `router { … }`. Each method returns `CommandApplier` (supports `infix withConfig { … }`). Methods:

| Category | Methods |
|---|---|
| Navigation | `navigate(screen)` (→ `Show` if `DialogScreen`, else `Forward`), `replace(screen)`, `newRoot(screen)` (BackTo(null)+Replace), `backTo(screen?)`, `exit()`, `finishRoot()` (BackTo(null)+Back), `newChain(vararg screens)` |
| Child chain | `startChildChain(screen)`, `finishChildChain()`, `backToFirstInChildChain()`, `newRootScreenCurrentChildChain(screen)`, `backToOrNavigate(screen)` |
| Dialogs | `show(dialog)`, `dismiss(dialog)`, `dismissCurrent()` |
| Authorization | `openLogin()`, `openRegistration()`, `closeLoginOnSuccess(isBackToRoot = false)`, `closeRegistrationOnSuccess()`, `backToAuthorization()` |
| Non-nav action | `doAction { }` (sync), `doSuspendAction { }` (delegated to `processScope` via `SuspendActionCallback`) |

### CommandConfig DSL (`withConfig { … }` = `CommandConfigBuilder`)
```kotlin
data class CommandConfig(
    val isAuthRequire: Boolean,
    val dialogParams: DialogParams,
    val authConfig: AuthConfig,
)
```
- `isAuthRequire` (default `false`) — triggers `AuthorizationInterceptor`: if not authorized, saves original as `pendingCommand`, opens login/auth; on success replays the command.
- `forDialog { key; isAllowingStateLoss; isShowMultipleDialog; shouldReattachParent }` — only meaningful for dialog commands (`show`/`dismiss`/`dismissCurrent`). Works with `OverlayDialogFragment`.
- `forAuthorization { dialog { … }; login { … }; registration { … } }` — parametrizes the login/registration flow (e.g. `isFromStartScreen`, `isBackToRoot`, `registrationTypes`).

### Dialog model
- `DialogScreen : Screen` — marker interface with `createDialog(factory)`. Build screens via `DialogScreen(key = …) { factory -> … }`.
- `DialogParams(key, isAllowingStateLoss, isShowMultipleDialog, shouldReattachParent)`.
- `defaultDialogParams` / `defaultAuthConfig` / `defaultCommandConfig` — reference values.

### Holders and providers
- `RouterHolder` (singleton per container) — stores routers in `LinkedHashMap<RouterKey, RouterEntry>`:
  - Keys: `RouterKey.Root` (Activity), `RouterKey.TabContainer`, `RouterKey.Aggregator`.
  - Exposed: `router` (top), `activityRouter`, `tabContainerRouter`, `aggregatorRouter`, `parentRouter`.
  - `attachRouter(key, router)` on container start; `detachRouter(key)` on `onDestroy`.
- `XPlatformRouterProvider` — `getRouter()` creates and configures a new router; `configureRouter(router)` wires auth callbacks. Implemented only in the `app` module.
- `LocalCiceroneHolder` — Cicerone holder keyed by `RouterKey`.

### Navigation stack (internal, read via ops, usually don't touch)
- `NavigationStackHolder(interceptor)` — `MutableStateFlow<NavigationStack>` source of truth.
- `NavigationStack` is a list of `NavigationEntry`: `Single(StackEntry)`, `Chain.Child(root, screens)`, `Chain.Auth(tag, root, screens)`.
- Dispatch methods update the stack **and** return a list of `NavigationCommand` (Forward/Replace/Back/BackTo/NewRoot/FinishRoot/StartChildChain/FinishChildChain/NewRootCurrentChildChain/BackToOrNavigate/NewChain/ShowDialog/DismissDialog/DismissCurrentDialog/Action/SuspendAction/DispatchCommand). Cicerone executes these via `executeCommands(...)`.
- Not managed by FragmentManager — FragmentManager is not the source of truth. If a dialog was not opened through `XPlatformRouter`, it will not appear in the stack (rule: always open through the router).

### Opt-in annotations
- `@RouterConfigurationApi` (`ERROR`) — guards router callback setters. Only `XPlatformRouterProviderImpl` should opt in.
- `@AuthorizationScreenUsageApi` (`ERROR`) — guards direct `authScreenFactory` usage. All auth navigation must go through the router.
- `@XPlatflormRouterDSL` / `@AuthScreenDSL` / `@DialogParamsDSL` — DSL scope markers.

## 2. Best Practices

### Always use DSL, never raw Cicerone
✅ `router { navigate(settingsScreenFactory.getScreen()) }`
❌ `router.executeCommands(Forward(settingsScreenFactory.getScreen()))` — bypasses `NavigationStackHolder` and `AuthorizationInterceptor`, desyncs virtual stack.

### Declare auth requirement via `isAuthRequire`, never with manual branching
✅
```kotlin
router {
    navigate(betHistoryScreen) withConfig { isAuthRequire = true }
}
```
❌
```kotlin
if (isAuthorized) router { navigate(betHistoryScreen) }
else router { openLogin() }   // no pendingCommand — user lands on previous screen, not on betHistoryScreen
```
Reason: manual branch does not save `pendingCommand`; auto-replay after login is lost.

### One `router { … }` block per related sequence (atomic)
✅ Batch related commands in one block:
```kotlin
router {
    dismissCurrent()
    navigate(resultScreen)
}
```
❌ Splitting related commands across two `router { … }` blocks — two configurators, not atomic, unpredictable interleaving.

### Always use `withConfig` for dialog keys / auth / state loss params
✅
```kotlin
router {
    dismissCurrent() withConfig {
        forDialog {
            key = screenKey
            isAllowingStateLoss = true
        }
    }
}
```

### Pass parameters to login/registration via `forAuthorization { … }`
```kotlin
router {
    openLogin() withConfig {
        forAuthorization {
            login {
                isFromStartScreen = true
                isBackToRoot = true
            }
        }
    }
}

router {
    openRegistration() withConfig {
        forAuthorization {
            registration { registrationTypes = registrationTypes }
        }
    }
}
```

### Obtain the router via `XPlatformRouterProvider`, never `XPlatformRouter()` directly
✅ `val router = xPlatformRouterProvider.getRouter()` (or `configureRouter(router)` if you already have one).
❌ `val router = XPlatformRouter()` — auth callbacks, suspend-action callback and screen factories are not wired → `isAuthorized()` is false forever, auth chain never starts.

### In `ViewModel`, always call via injected `XPlatformRouter`
- Inject `XPlatformRouter` via the assisted factory (`AssistedViewModelFactory` / `SavedStateRouterViewModelFactory`). Do NOT resolve the router from Fragment inside business logic.

## 3. Anti-Patterns (FORBIDDEN)

### ❌ References to ViewModel / Context / streams / coroutines inside `doAction { }`
`doAction` runs synchronously on the Main thread inside `applyCommand()`. It must not:
- call `viewModel.x()` or `viewModelScope.launchJob { … }` (leaks, race, scope reset on process death);
- call `flow.collect { … }` or `withContext(Dispatchers.IO) { … }` (suspend code — impossible here);
- hold `Context` / `View` references (leaks).

✅ `router { doAction { analytics.trackEvent("screen_opened") } }` — simple, synchronous, no external deps.
✅ For suspend work — use `doSuspendAction { repository.clearCache() }` (dispatched into the app-owned `processScope`).

### ❌ Bypassing DSL via `(router as BaseRouter).executeCommands(...)`
Virtual stack desync, auth interception lost, dialogs untracked.

### ❌ Opting into `@RouterConfigurationApi` from feature modules
Only `XPlatformRouterProviderImpl` in `app` configures the router. Feature modules calling `setAuthorizeCallback { … }` overwrite global behavior and break auth everywhere.

### ❌ Using `authScreenFactory` directly
Guarded by `@AuthorizationScreenUsageApi`. All auth navigation goes through `openLogin` / `openRegistration` / `closeLoginOnSuccess` / `closeRegistrationOnSuccess` / `backToAuthorization`.

### ❌ Opening fragments/dialogs through `fragmentManager.commit(...)` instead of the router
The virtual stack won't know about them → `dismissCurrent()` / auth detection / child chain logic break.

## 4. Testing — RouterVerificationScope

Use utilities from `:core:test` (see `xbet-testing` skill).

```kotlin
private val router: XPlatformRouter = mockk(relaxed = true)   // always relaxed

@Test
fun `WHEN onBackPressed EXPECT router exit`() = runTest {
    viewModel.onBackClicked()
    advanceUntilIdle()
    verifyRouter(router) { exit() }
}

@Test
fun `WHEN onSupportMenuClicked EXPECT navigate to contacts screen`() = runTest {
    val screen = mockk<Screen>()
    every { rulesScreenFactory.getContactsFragmentScreen(true) } returns screen

    viewModel.onSupportMenuClicked(mockSupportType, showNavBar = true)

    verifyRouter(router) { navigate(any()) }
    verify { rulesScreenFactory.getContactsFragmentScreen(true) }
}
```

Rules:
- `router` is always `mockk(relaxed = true)` / `RelaxedMock()`. Non-relaxed mocks fail on internal `BaseRouter` calls.
- Assertion order: verify on `router` **first**, only then on the screen factories (the factory is invoked as part of the router call chain, so ordering of verify blocks matters).
- Three shapes: `verifyRouter` (unordered, like `verify`), `verifyRouterOrder` (ordered, intermediates allowed), `verifyRouterSequence` (exact sequence, no extra calls).

## 5. Related Skills
- `xbet-viewmodel` — how router is injected into ViewModels / delegates.
- `xbet-testing` — full testing toolkit (`verifyRouter*`, `FlowTestResultHandler`, `TestCoroutinesInitializer`).
- `xbet-udf-architecture` — where navigation intent enters the UDF loop (typically `SideEffect` → Fragment/Compose triggers router).
- `xbet-project-context` — feature `navigation/` directory contract (screen factories in `api`, wiring in `impl`).
