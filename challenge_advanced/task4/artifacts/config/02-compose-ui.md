---
name: JarvisChat Compose UI
globs: "**/presentation/**/*.kt"
---

Compose Multiplatform + Material3. Screen composables live in `presentation/`, reusable pieces in `presentation/ui/`.

- Screen takes the UI model and a single action sink:
  `@Composable internal fun ChatScreen(uiModel: ChatUiModel, onAction: (ChatAction) -> Unit)`.
- `Modifier` is the first optional parameter and has a default: `modifier: Modifier = Modifier`.
- Composable never reads a ViewModel field directly. It receives `*UiModel` only.
- Collect state with `collectAsStateWithLifecycle()`.
- No business logic, no mapping, no formatting inside a composable. That belongs to `*UiMapper`.
- Slot parameters are trailing lambdas named `content`.
- No hardcoded colors or sizes. Use `MaterialTheme.colorScheme` and `dp` constants declared as `private val`.
- Preview functions are not written unless asked.
