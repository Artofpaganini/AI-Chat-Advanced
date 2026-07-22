---
name: xbet-testing
description: "Use when writing unit tests in Mobile_Android_OnexBet — testing UdfBaseViewModel / UdfBaseDelegate, using TestCoroutinesInitializer with testScope/testDispatcher, asserting Flow emissions via flow.handleTest(scope), verifying XPlatformRouter calls via verifyRouter / verifyRouterOrder / verifyRouterSequence, parametrizing tests with @SealedClassesSource, or setting up MockK with TestInitializer"
---

# core:test — Testing Reference

Module path: `core/test`. Package root: `org.xplatform.test.utils.*`.

Project testing framework: **JUnit 5**, **MockK**, **kotlinx-coroutines-test**. Add `testImplementation project(':core:test')` to any test-carrying module.

## 1. Module Surface

### Base interfaces
- `TestCoroutinesInitializer` — implement in classes that need `TestDispatcher` + `TestScope`. Sets `Dispatchers.setMain(testDispatcher)` in `@BeforeAll`, resets in `@AfterAll`, cancels `testScope` in `@AfterEach`, calls `MockKAnnotations.init(this)` / `unmockkAll()`.
  ```kotlin
  @ExperimentalCoroutinesApi
  @ExtendWith(TestCoroutinesInitializerExtension::class)
  interface TestCoroutinesInitializer {
      var testDispatcher: TestDispatcher
      var testScope: TestScope
      @BeforeEach fun setUp() { MockKAnnotations.init(this) }
      @AfterEach  fun tearDown() { unmockkAll() }
  }
  ```
- `TestInitializer` — lightweight MockK `@BeforeEach`/`@AfterEach` wiring **without** coroutine infrastructure. Use only for tests that do not involve coroutines/flows/ViewModels.
- `TestCoroutinesInitializerExtension` — JUnit 5 extension that injects `testDispatcher` (`StandardTestDispatcher`) and `testScope` into the test instance and swaps `Dispatchers.Main`.

### Flow testing
`FlowTestResultHandler<T>` + `flow.handleTest(scope)` extensions:
- `Flow<T>.handleTest(scope: CoroutineScope)` — start collecting on the given scope.
- `Flow<T>.handleTest(scope: TestScope)` — start collecting and `advanceUntilIdle()`.
- `Flow<T>.handleTest(scope: TestScope, delayTime: Duration)` — start collecting and `advanceTimeBy(delayTime)`.
- `Flow<T>.handleTest(scope: TestScope) { … }` — inline DSL variant that runs the block and calls `finish()` automatically.

Assertions on the handler:
| Method | Purpose |
|---|---|
| `assertValues(values: List<T>)` / `assertValues(vararg)` | Exact full list match in order |
| `assertValue(expected)` | Last emitted value equals `expected` |
| `assertValueOrNull(expected)` | Last emitted value equals `expected` (nullable) |
| `assertAny { it }` | Some emitted value matches predicate |
| `assertChecks(vararg checks)` | Per-index predicate checks + debug print of values |
| `assertNoValues()` | Nothing emitted |
| `assertNoErrors()` | No collection errors |
| `assertError(expected)` | Last error equals `expected` |
| `assertErrorType(Class)` | Last error is instance of `Class` |
| `getValues()` / `getErrors()` | Read raw collected data |
| `finish()` | **Must be called** — cancels the collector job, clears buffers |

⚠️ `JupiterTestFlowObserver` exists but is deprecated. **New tests must use `FlowTestResultHandler`** (`handleTest(...)`).

### Router verification
Re-exports `RouterVerificationScope` + three top-level functions from `TestNewOneXRouter.kt`:
- `verifyRouter(router, …) { … }` — MockK `verify` semantics (unordered, at-least-once).
- `verifyRouterOrder(router, …) { … }` — `verifyOrder` semantics (ordered, intermediates allowed).
- `verifyRouterSequence(router, …) { … }` — `verifySequence` semantics (exact, no intermediates).

Inside the block you get the same DSL as the production configurator: `navigate(screen)`, `replace(screen)`, `show(dialog)`, `newRoot(screen)`, `exit()`, `backTo(screen?)`, `openLogin()`, `openRegistration()`, `closeLoginOnSuccess(isBackToRoot)`, `closeRegistrationOnSuccess()`, `dismiss(dialog)`, `dismissCurrent()`, `newChain(vararg screens)`, `startChildChain(screen)`, `finishChain()` (= `finishRoot`), `finishChildChain()`, `backToOrNavigate(screen)`, `doAction(...)`, `doSuspendAction(...)`, `newRootScreenCurrentChildChain(screen)`, `backToAuthorization()`. Plus MockK matchers scoped to the verification: `any<T>()`, `match<T> { … }`, `eq(v)`, `ofType<T>()`, `ofType(cls)`. Each call returns a `VerificationCommandApplier` supporting `infix withConfig { … }`.

### Parametrized tests
- `@SealedClassesSource(factoryClass = DefaultTypeFactory::class, names = […], mode = INCLUDE|EXCLUDE)` — JUnit 5 `ArgumentsSource` that enumerates leaves of a sealed hierarchy. Use in `@ParameterizedTest`:
  ```kotlin
  @ParameterizedTest
  @SealedClassesSource(names = ["Success", "Error"], mode = INCLUDE)
  fun `handles all known states`(state: LoadState) { … }
  ```
  `DefaultTypeFactory` creates leaves via `objectInstance` for `data object` or via primary constructor with primitive defaults (0 / "" / false / null).

## 2. Test Layout Rules

- **Test class name:** `*ViewModelTest`, `*DelegateTest`, `*MapperTest`, `*UseCaseTest`, `*NavigatorTest`.
- **Location:** `src/test/java` mirroring the main package.
- **Method names:** `WHEN <trigger> EXPECT <outcome>` (backticked). For preconditions use `AND`:
  ```kotlin
  fun `WHEN StartCallProcess AND network available EXPECT ShowConnectionError`() = runTest { … }
  ```
- **Section comments inside tests:** `// Prepare` → `// Do` → `// Check`.

## 3. Best Practices

### ViewModel tests
- Subject: always test `state` (internal State), **not** `UiState`. Mapper gets its own `*MapperTest`.
- Inject `testDispatcher` into the constructor everywhere the ViewModel needs a `CoroutineDispatcher` (including `UdfDispatchers { map = testDispatcher, work = testDispatcher }`).
- After `onAction(...)` call `advanceUntilIdle()` whenever coroutines fire.
- Read `viewModel.state` for assertions:
  ```kotlin
  assertEquals(expected, viewModel.state.isNetworkAvailable)
  ```
- When asserting `SideEffect` — always use `flow.handleTest(testScope)`, call `assertValues(...)` then `finish()`:
  ```kotlin
  val actual = viewModel.getSideEffect().handleTest(this)
  actual.assertValues(expected).finish()
  ```
- If the flow under test emits several SideEffects, consume them one by one via `viewModel.onAction(Action.Internal.HandleSideEffect)` between `advanceUntilIdle()` calls — without `handleSideEffect()` the queue stalls on the first effect.
- If effects come from different scopes/coroutines, use `advanceTimeBy(delay)` instead of `advanceUntilIdle()` to reach a deterministic slice.

### Router tests
- `router = mockk(relaxed = true)` (or `RelaxedMock()`). `BaseRouter` has many internal calls — non-relaxed fails.
- Screen factories: `mockk(relaxed = true)` or `every { factory.getScreen(...) } returns mockk()` for specific cases.
- Verify on the `router` first, then verify on `screenFactory` — router is called first in the production chain.
- Choose the right flavor:
  - `verifyRouter` — "these calls happened, order irrelevant".
  - `verifyRouterOrder` — "A happened before B, other calls between are fine".
  - `verifyRouterSequence` — "exactly A, B, C in this order, nothing else".

### Mapper tests (`*MapperTest`)
- Instantiate mapper directly with real/fake deps (no ViewModel). Feed a handcrafted `State` and assert the resulting `UiState`.
- For `UiMapper` implementations with `contentHolder`/`contentSource`, verify that a second `invoke(state)` with identical sub-state does not change `uiValue` (stability guarantee).

### Delegate tests
- Same skeleton as ViewModel tests. Drive via `delegate.onAction(suspend)` inside `runTest` — it's suspend. Read `delegate.delegateState`, collect `delegate.getDelegateSideEffect().handleTest(this)`.

## 4. Minimal Test Skeleton

```kotlin
@ExperimentalCoroutinesApi
class SomeViewModelTest : TestCoroutinesInitializer {

    override lateinit var testDispatcher: TestDispatcher
    override lateinit var testScope: TestScope

    private val router: XPlatformRouter = mockk(relaxed = true)
    private val useCase: SomeUseCase = mockk()
    private val screenFactory: SomeScreenFactory = mockk(relaxed = true)

    private lateinit var viewModel: SomeViewModel

    @BeforeEach
    override fun setUp() {
        super.setUp()
        viewModel = SomeViewModel(
            router = router,
            useCase = useCase,
            screenFactory = screenFactory,
            dispatchers = udfDispatchers(map = testDispatcher, work = testDispatcher),
        )
    }

    @Test
    fun `WHEN OnLoadClick AND useCase returns items EXPECT state has items AND isLoading false`() = runTest {
        // Prepare
        coEvery { useCase.invoke() } returns listOf(item1, item2)

        // Do
        viewModel.onAction(SomeAction.User.OnLoadClick)
        advanceUntilIdle()

        // Check
        assertEquals(listOf(item1, item2), viewModel.state.items)
        assertEquals(false, viewModel.state.isLoading)
    }

    @Test
    fun `WHEN OnBackClick EXPECT router exit`() = runTest {
        viewModel.onAction(SomeAction.User.OnBackClick)
        advanceUntilIdle()

        verifyRouter(router) { exit() }
    }
}
```

## 5. Anti-Patterns (FORBIDDEN)

- ❌ Writing new tests with `JupiterTestFlowObserver` — deprecated. Use `flow.handleTest(scope)`.
- ❌ Mocking `XPlatformRouter` without `relaxed = true` — will fail on internal `BaseRouter` calls.
- ❌ Asserting `UiState` inside a `*ViewModelTest` — write a separate `*MapperTest` for UiState.
- ❌ Forgetting `finish()` on a `FlowTestResultHandler` — leaks the collector job across tests and pollutes state.
- ❌ Using `Dispatchers.Main`/`Dispatchers.IO` directly in ViewModel deps — inject `UdfDispatchers` with `testDispatcher` in tests.
- ❌ Using raw `runBlocking` — always `runTest { … }` from `kotlinx-coroutines-test`.
- ❌ Reading `UiState` from `viewModel.getUiState().first()` as a shortcut instead of asserting `state`.
- ❌ Calling `mockk<Screen>(relaxed = false)` and then failing to set up `screenKey` — prefer `mockk<Screen>()` and pair with `every { factory.getScreen(...) } returns screen`.

## 6. Checklist Before Merging Tests

- [ ] Test class implements `TestCoroutinesInitializer` when coroutines/flows are involved (`TestInitializer` otherwise).
- [ ] `testDispatcher` piped into ViewModel via `UdfDispatchers`.
- [ ] Test name follows `WHEN … EXPECT …` (with optional `AND`).
- [ ] `Prepare / Do / Check` sections present.
- [ ] `advanceUntilIdle()` after every `onAction` that triggers coroutines.
- [ ] `FlowTestResultHandler.finish()` called.
- [ ] `verifyRouter`/`verifyRouterOrder`/`verifyRouterSequence` picked according to expected ordering.
- [ ] Internal State asserted, not UiState (UiState has its own mapper test).

## 7. Related Skills
- `xbet-viewmodel` — ViewModel/Delegate shape and State mapping being tested.
- `xbet-navigation` — router API surface being verified.
- `xbet-udf-architecture` — why we test `state` and `SideEffect` separately.
- `xbet-project-context` — module packaging (tests live in `src/test/java` mirroring main).
