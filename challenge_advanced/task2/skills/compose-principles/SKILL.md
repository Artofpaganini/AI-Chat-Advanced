---
name: compose-principles
description: "Shared Jetpack/Compose Multiplatform best practices: UDF integration, recomposition, naming conventions, parameter ordering, Content Slot API, Modifier patterns. Used by xbet-compose-expert and alva-android-ui-expert."
---

# Compose Principles

Shared rules for Jetpack Compose / Compose Multiplatform UI in any project. Project-specific extras (design-system prefix, tech stack, visibility rules) live in the calling agent's body.

## State and UDF

- **Unidirectional data flow.** State flows down (as parameters); events flow up (callbacks / `onAction`). Never update state from UI except via callback to ViewModel.
- **State in composables:**
  - `remember` / `rememberSaveable` for composition-scoped state.
  - `collectAsStateWithLifecycle` for Flow from ViewModel.
  - Don't hold business state in composables when it belongs in the ViewModel.
- **State hoisting:**
  - For reusable composables, expose `value: T` and `onValueChange: (T) -> Unit`. The lambda parameter must have a meaningful name — never leave it as `it`.
  - Keep composables stateless when caller must control state.
- **Composable parameters:**
  - Prefer minimal, typed parameters to limit recomposition scope.
  - Group many parameters into a data class only if it improves readability.
- **Immutability.** Prefer immutable `UiState` (data class with `val`). Use copy/update in ViewModel; never mutate in UI.
- **Stateless functions.** Stateless-first UI is easier to test and reuse. Always think "can this function be reused?". For dynamic content use Content Slot API / Compound Compose Functions.

### UDF integration code

State collection:
```kotlin
val uiState by viewModel.getUiState()
    .collectAsStateWithLifecycle()
```

Side effects:
```kotlin
LaunchedEffect(Unit) {
    viewModel.getEvent().collect { effect ->
        // Handle navigation, toasts, dialogs
        viewModel.handleSideEffect()
    }
}
```

Actions:
```kotlin
Button(onClick = { viewModel.onAction(Action.User.ButtonClicked) })
```

### Preview-driven development

Generate `@Preview` for every composable. Use `PreviewParameterProvider` (separate class, separate file) for sample data:

```kotlin
// HelperUiModelPreviewProvider.kt
internal class HelperUiModelPreviewProvider : PreviewParameterProvider<BottomLaneUiModel.HelperUiModel> {
    override val values = sequenceOf(
        BottomLaneUiModel.HelperUiModel(
            titleText = "Helper title",
            subTitleText = "Helper subtitle",
            settingsText = "Settings",
            isVisible = true
        ),
        BottomLaneUiModel.HelperUiModel(
            titleText = "Helper title veeeeery loooooooong",
            subTitleText = "Helper subtitle veeeeery loooooooong",
            settingsText = "Settings",
            isVisible = true
        )
    )
}

@Composable
@Preview(showBackground = true) // also: small/medium phone, tablet
private fun HelperPreview(
    @PreviewParameter(HelperUiModelPreviewProvider::class)
    helperUiModel: BottomLaneUiModel.HelperUiModel
) { ... }
```

## Performance and Structure

- **Avoid unnecessary recomposition:**
  - Pass stable / lambda-free args where possible.
  - Use `remember` and `key()` for lists. Inside `list.forEach { ... }` in composable code, wrap iterations with `key(...)`.
  - Use `fastForEach` / `fastForEachIndexed` / `fastMap` (project utilities) in hot layout paths.
- **Delegate logic to ViewModel.** Keep composables focused on UI.
- **Side effects.** `LaunchedEffect` / `DisposableEffect` for lifecycle-bound effects. Don't run business logic or state updates inside composition.

## Naming Patterns for Composable Functions

The design-system prefix is **project-specific** (e.g. `Ds*` for OnexBet, `Alva*` for Alva). The calling agent specifies its own prefix; the rules below apply universally.

1. `<DSPrefix>[Component type]` — used when the composable is part of the **Design System** and can be reused across modules. Example: `<DSPrefix>Header`.
2. `[Feature]/[Screen] + [Component type]` — used when the composable belongs to a specific screen inside a feature and should NOT be reused elsewhere. Example: `AuthHeader` / `RegistrationHeader`.
3. `[Parent component type] + [Role]` — used when the composable is a nested part of another composable and has no meaning outside the parent context. Example: `AuthHeaderTitle`.

### Forbidden suffixes/prefixes

`View` / `Component` / `Element` / `Get` / `Set` / `Listener` / `Modifier` / `Part` / `SubElement` / `SubItem` / `Composition` / `Compose` — **NEVER** use these in composable function names.

## Custom Modifier Naming

Bad:
```kotlin
fun Modifier.roundedCornerModifier(radius: Dp)
fun Modifier.getRippleClickableElement()
fun Modifier.setSomeEffectBackground()
```

Good:
```kotlin
fun Modifier.roundCorner(radius: Dp)
fun Modifier.clickableWithRippleEffect()
fun Modifier.backgroundWithSomeEffect()
```

## Composable Function Parameter Order

Recommended order for readability and consistency. Any parameter may be nullable.

### 1. Modifier
- Always present if the composable renders content.
- Always the first parameter.
- Exactly one `Modifier` per composable.
- `Modifier` must have a default (`= Modifier`).

```kotlin
@Composable
fun SomeFunc(
    modifier: Modifier = Modifier,
    text: String
) {
    Box(modifier = modifier) { // applied only to the top-level composable in the hierarchy
        Text(text)
    }
}
```

### 2. External data
```kotlin
user: State<User>, // if this is a leaf composable, use `user: User` directly
isEnabled: Boolean
```

### 3. Component-specific parameters
Parameters affecting display or behavior (analogous to `Row`/`Column` parameters):
```kotlin
horizontalArrangement: Arrangement.Horizontal = Arrangement.Start,
verticalAlignment: Alignment.Vertical = Alignment.Top,
textStyle: TextStyle = LocalTextStyle.current
```

### 4. Action callback (`onAction`)

For each composable's actions:

**< 3 actions** — create 1-2 lambdas with the pattern `on + [Action]`:

```kotlin
@Composable
internal fun SomeFunc(
    modifier: Modifier = Modifier,
    onButtonClick: () -> Unit,
    onValueChange: (String) -> Unit,
) { }

@Composable
internal fun SomeOtherFunc(
    modifier: Modifier = Modifier,
    onAction: (SomeAction) -> Unit,
) {
   SomeFunc(
       onButtonClick = { onAction.invoke(SomeClick()) },
       onValueChange = { value -> onAction.invoke(SomeValueChange(value)) }
   )
}
```

**>= 3 actions** — create a `sealed` class/interface (`SomeAction`) covering all actions and emit it via a single `onAction` callback. Exception: Design System components (see below).

```kotlin
@Composable
internal fun SomeFunc(
    modifier: Modifier = Modifier,
    onAction: (SomeAction) -> Unit,
) { }
```

### Design System components — different rule

For DS components, every outgoing action must be a separate **nullable** lambda. This way consumers use only the lambdas they actually need, without having to filter a `when` over a sealed action.

Bad (sealed action — forces consumer to filter):
```kotlin
@Composable
internal fun <DSPrefix>SportEventCard(
    modifier: Modifier = Modifier,
    item: <DSPrefix>EventCardUiItem,
    onAction: (<DSPrefix>EventCardAction) -> Unit  // ← consumer must filter all branches
) { ... }
```

Good (nullable lambdas — consumer picks what's needed):
```kotlin
@Composable
internal fun <DSPrefix>SportEventCard(
    modifier: Modifier = Modifier,
    item: <DSPrefix>EventCardUiItem,
    onNotificationBtnClick: ((gameId: Long) -> Unit)? = null,
    onFavoriteBtnClick: ((gameId: Long, sportId: Long) -> Unit)? = null,
    onBroadcastBtnClick: ((gameId: Long) -> Unit)? = null,
    onZoneBtnClick: ((gameId: Long, sportId: Long) -> Unit)? = null,
    onCardClick: ((someModel: SomeModel) -> Unit)? = null,
    onMarketClick: (() -> Unit)? = null,
    onMarketLongClick: (() -> Unit)? = null,
    onExpandBtnClick: (() -> Unit)? = null,
    onAllMarketsBtnClick: (() -> Unit)? = null,
) { ... }
```

### 5. Content Slot (if any)

```kotlin
topBar: @Composable () -> Unit = null,
bottomBar: @Composable () -> Unit = null,
snackbarHost: @Composable () -> Unit = null,
floatingActionButton: @Composable () -> Unit = null,
dialog: @Composable ColumnScope.() -> Unit = null,
someOtherContent: @Composable RowScope.() -> Unit = null,
```

Full-parameter example:
```kotlin
@Composable
internal fun SomeFunc(
    modifier: Modifier = Modifier,
    uiState: State<SomeUiModel>,    // or `uiModel: SomeUiModel` if leaf
    horizontalArrangement: Arrangement.Horizontal = Arrangement.SpaceBetween,
    onAction: (SomeAction) -> Unit,
    onBottomContentAction: (BottomAction) -> Unit, // separate Action for a sub-block when needed
    floatingActionButton: @Composable () -> Unit,
    waterMark: (@Composable () -> Unit)? = null,
    topContent: (@Composable ColumnScope.() -> Unit)? = null,
    middleContent: (@Composable ColumnScope.() -> Unit)? = null,
    bottomContent: (@Composable ColumnScope.() -> Unit)? = null,
) { ... }
```

### Naming a Content Slot

- If the slot's content is fixed in role (e.g. `floatingActionButton` is always a button) — name it after what it is.
- If the slot's content is dynamic and unknown — use abstract name + `Content`, e.g. `topContent`.

## UI Design — From Simple to Complex

When designing a new component, **always start from the smallest/lightest Compose primitive** and only escalate nesting if the simpler version doesn't work.

Example: composite element with a 40×40 icon, top-right text 20×40, bottom-right text 20×30.

Bad (two levels of nesting):
```kotlin
Row(modifier = modifier) {                         // level 1
    Icon(
        imageVector = ImageVector.vectorResource(R.drawable.ic_game),
        modifier = Modifier.size(40.dp),
        contentDescription = null
    )
    Column(modifier = Modifier.height(40.dp)) {    // level 2
        Text(
            modifier = Modifier.height(20.dp).widthIn(max = 40.dp),
            maxLines = 1,
            text = "100",
        )
        Text(
            modifier = Modifier.height(20.dp).widthIn(max = 30.dp),
            maxLines = 1,
            text = "Pick",
        )
    }
}
```

Good (single Box with alignment):
```kotlin
Box(modifier = modifier.size(width = 80.dp, height = 40.dp)) { // level 1
    Icon(
        modifier = Modifier.align(Alignment.CenterStart).size(40.dp),
        imageVector = ImageVector.vectorResource(R.drawable.ic_game),
        contentDescription = null
    )
    Text(
        modifier = Modifier.align(Alignment.TopEnd).height(20.dp).widthIn(max = 40.dp),
        maxLines = 1,
        text = "100"
    )
    Text(
        modifier = Modifier.align(Alignment.BottomEnd).height(20.dp).widthIn(max = 30.dp),
        maxLines = 1,
        text = "Pick"
    )
}
```

For more complex layouts (e.g. toolbar + LazyColumn), prefer **custom Layout** with explicit measurement.

**Avoid `Scaffold`** — it's one of the heaviest layouts with a lot of internal logic. Prefer a custom Layout.

### Pattern: collapsing toolbar via custom Layout

```kotlin
private const val COLLAPSING_CONTENT_KEY = "COLLAPSING_CONTENT_KEY"
private const val CONTENT_KEY = "CONTENT_KEY"
private const val TOOLBAR_KEY = "TOOLBAR_KEY"

@Composable
internal fun CollapsingToolbarContainer(
    modifier: Modifier = Modifier,
    nestedScrollableState: ScrollableState,
    state: CollapsingToolbarState = rememberCollapsingToolbarState(),
    flingBehavior: FlingBehavior = ScrollableDefaults.flingBehavior(),
    toolbar: (@Composable (Modifier) -> Unit),
    content: @Composable (Modifier) -> Unit,
    collapsableContent: (@Composable (Modifier) -> Unit)? = null
) {
    var collapsableContentHeight by rememberMutableState(0)
    var toolbarContentHeight by rememberMutableState(0)
    val safeNonCollapsableHeight by rememberDeriveState {
        toolbarContentHeight.coerceAtMost(collapsableContentHeight)
    }

    Layout(
        content = {
            collapsableContent?.invoke(Modifier.layoutId(COLLAPSING_CONTENT_KEY))
            content.invoke(Modifier.layoutId(CONTENT_KEY))
            toolbar.invoke(Modifier.layoutId(TOOLBAR_KEY))
        },
        modifier = modifier
            .clipToBounds()
            .fillMaxSize()
            .scrollable(
                state = state.scrollableState,
                orientation = Orientation.Vertical,
                enabled = !state.isFullyCollapsed,
                flingBehavior = rememberCollapsingToolbarFlingBehavior(
                    flingBehavior = flingBehavior,
                    nestedScrollableState = nestedScrollableState
                )
            )
            .nestedScroll(state.nestedScrollConnection)
    ) { measurables, constraints ->
        if (measurables.isEmpty()) return@Layout layout(0, 0) { }
        val height = constraints.maxHeight

        val placeables = measurables.fastMap { measurable ->
            when (measurable.layoutId) {
                COLLAPSING_CONTENT_KEY -> {
                    val p = measurable.measure(constraints.copy(minHeight = 0, maxHeight = Constraints.Infinity))
                    collapsableContentHeight = p.height
                    p
                }
                CONTENT_KEY -> measurable.measure(
                    constraints.copy(
                        minHeight = 0,
                        maxHeight = (height - safeNonCollapsableHeight).coerceAtLeast(0)
                    )
                )
                else -> {
                    val p = measurable.measure(constraints.copy(minHeight = 0))
                    toolbarContentHeight = p.height
                    p
                }
            }
        }
        state.maxCollapsableHeight =
            (collapsableContentHeight - safeNonCollapsableHeight).toFloat().coerceAtLeast(0f)
        layout(constraints.maxWidth, height) {
            val collapsedHeight = state.collapsedHeight.roundToInt()
            placeables.fastForEach { placeable ->
                when ((placeable.parentData as? LayoutIdParentData)?.layoutId) {
                    TOOLBAR_KEY -> placeable.placeRelative(0, 0)
                    COLLAPSING_CONTENT_KEY -> placeable.placeRelative(0, -collapsedHeight)
                    CONTENT_KEY -> placeable.placeRelative(0, collapsableContentHeight - collapsedHeight)
                }
            }
        }
    }
}
```

## Content Slot API — When and How

```kotlin
@Composable
@NonRestartableComposable
internal fun SomeFunc(
    modifier: Modifier = Modifier,
    topContent: (@Composable ColumnScope.() -> Unit),
    middleContent: (@Composable ColumnScope.() -> Unit),
    bottomContent: (@Composable ColumnScope.() -> Unit)? = null,
) {
    Column(modifier = modifier) {
        topContent.invoke()
        middleContent.invoke()
        bottomContent?.invoke()
    }
}
```

**Use Content Slot API when you need to:**
- Build a reusable component with variable content.
- Allow customization of individual parts of a component.
- Provide optional functionality that may or may not be present.
- Pass multiple `Modifier`s into one composable — child composables receiving secondary modifiers should live in their own slots.

**How to use:**
1. Decide whether you actually need slots. Typical cases:
   - Design System components.
   - Templates whose layout is shared but content varies by data.
   - Composables where you want to pass a secondary `Modifier` to a child.
2. Define the facade with base parameters and base logic.
3. Mark slots required (no default) or optional (nullable).
4. If recomposition shouldn't ripple — annotate the function `@NonRestartableComposable`.

**Lambda stability note.** Each Content Slot, when decompiled, becomes an anonymous class with one of the states: `Static` / `Stable` / `Unstable` / `Capture`. Choose slot signatures with stability in mind.

## Working with Modifier

### 1. Deferred composition

Some `Modifier`s evaluate not immediately but during their respective phase (Composition / Layout / Draw). Reading state inside a phase-specific lambda avoids unnecessary recomposition. Google recommends this when possible ([defer-reads](https://developer.android.com/develop/ui/compose/performance/bestpractices#defer-reads)).

Bad — reading animated state inside `background` (Composition phase):
```kotlin
@Composable
private fun SomeFunc() {
    val color = animateColorBetween(Color.Cyan, Color.Magenta)
    Box(
        Modifier
            .fillMaxSize()
            .background(color.value)
    )
}
```
Each color change triggers recomposition of `Box`.

Good — reading inside `drawBehind` (Draw phase):
```kotlin
@Composable
private fun SomeFunc() {
    val color = animateColorBetween(Color.Cyan, Color.Magenta)
    Box(
        Modifier
            .fillMaxSize()
            .drawBehind { drawRect(color.value) }
    )
}
```
No recomposition; only the Draw phase re-runs.

### 2. How padding works

`Modifier.padding` placed **before** the first Layout/Draw modifier in the chain behaves like `margin` in XML.

```kotlin
Box(modifier = Modifier.background(Color.LightGray)) {
    Text(
        text = "Some text",
        modifier = Modifier
            .padding(25.dp)              // margin — before size/background
            .size(150.dp)
            .background(Color.Yellow)
            .padding(25.dp)              // padding — after size/background
            .background(Color.Red)
    )
}
```

`Modifier.padding` placed **after** the first Layout/Draw modifier behaves like `padding` in XML.

**Use `padding` instead of `Spacer`.** Reasons:
- `padding` is not a Layout and doesn't directly depend on recomposition. It's recreated only when the screen recomposes or when downstream `Modifier.Node`s change.
- `padding` is cached because it uses a `Modifier.Node` structure internally.
- Composition time of `padding` is 1.5–2× faster than `Spacer`.

`Spacer` is justified **only** when filling a region with `weight`. Never as a margin replacement.

### 3. Don't return Modifier from a Composable function

Exception: modifiers that implement animations or hold `remember` (try to lift `remember` outside when possible).

Bad:
```kotlin
@Composable
fun SomeFunc(
    condition1: Boolean,
    condition2: Boolean,
    condition3: Boolean,
): Modifier = when {
    condition1 -> Modifier.background(Color.Red)
    condition2 -> Modifier.background(UiKitTheme.colors.primary, RoundedCornerShape(12.dp))
    condition3 -> Modifier.padding(12.dp).background(Color.Red)
    else -> Modifier.background(Color.Transparent)
}
```

Use instead:
- **Custom `Modifier.Node`** — caches logic and skips recreation when not needed. Subclass `Modifier.Node` and attach to a specific composable. Reference: https://developer.android.com/develop/ui/compose/custom-modifiers
- Build the modifier inline at the call site, attached to a specific composable.

### 4. Avoid `onSizeChanged` / `onGloballyPositioned`

These callbacks force a second layout/recomposition pass, costing an extra frame. With dynamic sizes, recomposition can grow geometrically.

Bad:
```kotlin
var imageHeightPx by remember { mutableStateOf(0) }

Image(modifier = Modifier.onSizeChanged { size -> imageHeightPx = size.height })
Text(modifier = Modifier.offset(y = imageHeightPx.toDp()))
```

Frame 1 (composition + recomposition):
- Layout phase measures `Image`; `onSizeChanged` fires; `imageHeightPx` is updated.
- `Text` reads `imageHeightPx` → recomposition.

Frame 2 (full layout): Both children draw.

**`onGloballyPositioned`** is even worse — it fires on every Layout phase entry. Worst cases: scroll, animation, content changes.

#### Alternatives

- **Best for complex scenarios:** custom `Layout`. Implement measurement and placement explicitly:
  ```kotlin
  @Composable
  fun CustomColumn() {
      Layout(
          content = { Image(); Text() },
          measurePolicy = { measurables, constraints ->
              val placeables = measurables.map { it.measure(constraints) }
              layout(constraints.maxWidth, constraints.maxHeight) {
                  var x = 0
                  var y = 0
                  placeables.forEach { p ->
                      p.placeRelative(x, y)
                      x += p.width
                      y += p.height
                  }
              }
          },
      )
  }
  ```
- **Best for light scenarios:** custom `Modifier.Node` that handles size/position internally.
- Or use deferred composition (with awareness of UX trade-offs).
- For initially-unknown child position, use `ParentDataModifier` + `Modifier.layoutId(...)`.
- `BoxWithConstraints` / `SubcomposeLayout` are HEAVIER than `onSizeChanged` — only use them for global control of full lists/screens (`SubcomposeLayout` powers `LazyColumn`/`LazyRow`).
- For changing content with `onGloballyPositioned`-style needs: subclass `Modifier.Node` implementing `GlobalPositionAwareModifierNode`.
- [`onLayoutRectChanged`](https://developer.android.com/reference/kotlin/androidx/compose/ui/layout/package-summary#%28androidx.compose.ui.Modifier%29.onLayoutRectChanged%28kotlin.Long,kotlin.Long,kotlin.Function1%29) is a lighter alternative once available in your dependency set.

## krozov-ai-tools — Slash Commands

Use these `Skill` commands when applicable:

| Command | When to Use |
|---|---|
| `/check-deps` | After modifying build files — scan dependencies for available updates |
| `/migrate-to-compose` | Full 7-phase migration of Android XML layouts to Jetpack Compose |
| `/code-migration` | Safe library migration (e.g. switching UI libs, async patterns) |
