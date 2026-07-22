---
name: alva-project-context
description: "Shared project context and rules for all alva agents (Alva — Kotlin Multiplatform / Compose Multiplatform baby-care app). Covers module visibility rule, feature packaging (api/impl + per-entity sub-directories), and cross-cutting Alva conventions."
---

# Alva — Project Context

Alva is a Kotlin Multiplatform (KMP) baby-care app with Compose Multiplatform for Android and iOS. Clean Architecture with UDF (Unidirectional Data Flow). Multi-module structure split across `androidApp`, `composeApp`, `core/*`, `feature/*`.

Full build / tooling / architecture rules live in the project root `CLAUDE.md`. This skill supplements it with visibility rules, module packaging and anything else shared across alva subagents.

## Code Search — ast-index by default

For ANY code search (find class / find symbol / find usages / find implementations / find file / class hierarchy / find callers / module deps / project map / project structure) **start with `ast-index`**. The user runs `ast-index watch` — the index is live; **do NOT run `ast-index update`**. Fall back to `Grep` only when the search is genuinely free-text (comments, log strings, error messages, non-code files).

---

## Feature Module Packaging

**Layer directories** (`data/` / `domain/` / `presentation/` / `di/` / `navigation/`) are split into **sub-directories grouped by entity type** — one entity per file in its matching sub-directory. Do not dump all UseCases / Repositories / Models into a single flat layer folder.

```
feature/<name>/
├── data/                    # (only in impl, see "Feature Module Structure" below)
│   ├── repository/          # *RepositoryImpl
│   ├── datasource/          # remote/local data sources (Ktor client, SQLDelight, DataStore)
│   ├── model/               # *DataModel / DTOs (Ktor @Serializable)
│   └── mapper/              # data → domain mappers
├── domain/
│   ├── usecase/             # use cases
│   ├── scenario/            # multi-step scenarios
│   ├── repository/          # repository interfaces (if exposed)
│   └── model/               # domain models (*Model)
├── presentation/
│   ├── viewmodel/           # UdfBaseViewModel subclasses (shared across Android/iOS)
│   ├── action/              # Action sealed hierarchies (User / Internal)
│   ├── state/               # State data classes
│   ├── sideeffect/          # SideEffect sealed hierarchies
│   ├── uistate/             # UiState + mappers from State
│   ├── delegate/            # UdfDelegate implementations
│   └── ui/                  # Compose Multiplatform screens / components
├── di/                      # Koin modules, factories
└── navigation/              # screen factories / nav routes (Compose Nav / nav3)
```

**Rule:** every new entity (use case, repository, mapper, delegate, model, etc.) goes into its own sub-directory within its layer. A new use case → `domain/usecase/<Name>UseCase.kt`; a new delegate → `presentation/delegate/<Name>Delegate.kt`.

**Exception — "main entity of the layer"** may live **directly in the layer root** (no sub-directory), because it's canonical for that slice and typically unique per feature:

| Layer | Main entity (root of layer) | Everything else (sub-directory) |
|---|---|---|
| `data/` | `<Name>RepositoryImpl.kt` | `datasource/`, `model/`, `mapper/` |
| `domain/` | *(none — all entities are typed: use cases, scenarios, models, repo interfaces)* | `usecase/`, `scenario/`, `repository/`, `model/` |
| `presentation/` | `<Name>ViewModel.kt` | `action/`, `state/`, `sideeffect/`, `uistate/`, `mapper/`, `delegate/`, `ui/` |
| `di/` | `<Name>Module.kt` (main Koin module) | submodules/, factories/, qualifiers/ if many |
| `navigation/` | `<Name>Screen.kt` / `<Name>Route.kt` (main screen factory / route) | nested screens/, dialogs/, params/ if many |

If there is more than one candidate for the "main entity" role (e.g. several RepositoryImpls in one feature), put all of them into the corresponding sub-directory — the root is reserved for single canonical entries.

---

## Code Style (Project-Specific — supplement to global CLAUDE.md)

- **Visibility — MANDATORY rule:** every declaration (class / interface / object / function / property / constructor / type alias / expect/actual) must be classified by its cross-module reach, and the modifier chosen accordingly:
  - **`public`** — ONLY if the declaration is consumed outside its own Gradle module (i.e. it is part of the module's `api` contract, used by `composeApp`, `androidApp`, `iosApp`, another feature, or a `:core:*` consumer). This includes `expect` declarations that need to be visible to another module, and any type that crosses the KMP framework boundary into Swift.
  - **`internal`** — REQUIRED if the declaration is consumed only within its own module. No exceptions. This includes: ViewModels (`UdfBaseViewModel` subclasses), Delegates, State / UiState / Action / SideEffect hierarchies, mappers, impl classes, Koin modules defined inside feature `impl`, private-looking helpers, Composable screens/components defined in feature `impl`, expect/actual pairs that do not cross modules, Ktor DTOs used by only one feature's data layer, etc.
  - **`private`** — when the declaration is used only inside the same file/class (normal Kotlin rule, not module-related).
  - Practical check: if the symbol is imported from another Gradle module, it MUST be `public`; otherwise it MUST be `internal`. Drop the default `public` modifier anywhere it shouldn't apply — unmarked Kotlin declarations are `public` by default, which is the most common violation.
  - **KMP specifics:**
    - `expect`/`actual` pairs that stay inside one module — `internal` on both sides.
    - If a shared-module ViewModel is consumed from `androidApp` and `iosApp`, the ViewModel class stays `internal` within the feature `impl`; expose a `public` factory / Koin definition in the feature `api` module instead.
    - iOS-exported types (classes that cross the KMP framework boundary into Swift) must be `public` — but only those types; every helper stays `internal`.
  - Examples:
    - ✅ `internal class ChildProfileViewModel : UdfBaseViewModel<…>` (consumed only inside `feature/child_profile/impl`)
    - ✅ `interface ChildProfileScreenFactory { fun create(...): Screen }` in `feature/child_profile/api` → stays `public` (crosses module boundary)
    - ❌ `class ChildProfileMapper` inside `impl` → must be `internal class ChildProfileMapper`
    - ❌ `fun Modifier.babyCardShadow(…)` inside a feature module → must be `internal` unless it is in `core/uikit`
- **Imports:** full imports (no star). Order per project ktlint/detekt config. Right margin 120.
- **Reformat:** reformat all changed/new code (ktlint).
- **Comments:** English. Keep existing unless wrong.
- **Sealed hierarchies:** prefer `sealed interface` with `data object` / `data class` / `value class`.
  - `@Immutable` on action/state interfaces where applicable.
  - Single-value wrappers: `@JvmInline value class`.
- **DI:** constructor injection; **Koin** at feature level (ViewModels, use cases, repositories, mappers). Feature-level Koin modules live in `feature/<name>/impl/di/`. Cross-feature bindings are exposed via `feature/<name>/api/di/`.
- **Avoid `object` (singleton declarations):** use `object` only as a last resort or when the user explicitly asks. Allowed exceptions: `data object` inside a `sealed interface` hierarchy, `companion object { fun empty() }` for presentation-layer models (State / UiState / UiModel — per CLAUDE.md). Prefer classes with DI instead of standalone `object`s.
- **Lambda parameters — always named, never implicit `it`:** give every lambda parameter an explicit meaningful name, including single-parameter lambdas.
  - ✅ `onValueChange = { newValue -> … }`, `items.map { item -> item.id }`, `flow.collect { state -> … }`
  - ❌ `onValueChange = { … }` (relies on `it`), `items.map { it.id }`, `flow.collect { … }`
- **Multi-part functions — split across files:**
  - **Composables:** if a `@Composable` screen or component is composed of several sub-composables, extract every sub-composable into its own file inside the `presentation/ui/` directory of the feature. Group related sub-composables using nested sub-directories under `ui/` when a screen has many parts (e.g. `presentation/ui/child_profile/header/HeaderBar.kt`, `presentation/ui/child_profile/header/HeaderAvatar.kt`).
  - **Mappers:** if a mapper delegates to several other mapper functions, extract every mapper into its own file inside the corresponding `mapper/` sub-directory (`data/mapper/` or `presentation/mapper/`).
  - **Preview providers:** each `PreviewParameterProvider` lives in its own file next to the composable it previews (same `ui/` sub-directory).

---

## Feature Module Structure — with `api` / `impl` split

Same sub-directory-per-entity rule applies inside each layer.

```
feature/<name>/api/                 # public contracts (KMP common code only)
  ├── di/                           # public Koin definitions / qualifiers
  ├── domain/
  │   ├── usecase/                  # use case interfaces
  │   ├── repository/               # repository interfaces (if exposed)
  │   └── model/                    # domain models (*Model)
  ├── navigation/                   # screen factories, nav routes, nav params
  └── presentation/
      └── model/                    # presentation models (*UiModel) if needed

feature/<name>/impl/                # implementation (KMP common + platform sources)
  ├── data/
  │   ├── repository/               # *RepositoryImpl
  │   ├── datasource/               # Ktor client, SQLDelight, DataStore, expect/actual sources
  │   ├── model/                    # *DataModel / DTOs (@Serializable)
  │   └── mapper/                   # data → domain mappers
  ├── di/                           # Koin modules (feature-scope), factories
  ├── domain/
  │   ├── usecase/                  # use case impl
  │   └── scenario/
  └── presentation/
      ├── viewmodel/                # UdfBaseViewModel subclasses (common)
      ├── action/ state/ sideeffect/ uistate/   # UDF sealed hierarchies
      ├── mapper/                   # State → UiState, domain → presentation
      ├── delegate/                 # UdfDelegate implementations
      └── ui/                       # Compose Multiplatform screens / components
```

Android/iOS-specific source sets (`androidMain`, `iosMain`) inside `impl` follow the same sub-directory layout as `commonMain` — a platform-specific `actual` mapper/datasource lives in the corresponding `mapper/` / `datasource/` sub-directory of its source set, not at the root.
