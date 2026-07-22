---
name: xbet-project-context
description: "Shared project context and knowledge for all xbet agents (Mobile_Android_OnexBet)"
---

# Mobile_Android_OnexBet — Project Context

## Code Search — ast-index by default

For ANY code search (find class / find symbol / find usages / find implementations / find file / class hierarchy / find callers / module deps / project map / project structure) **start with `ast-index`**. The user runs `ast-index watch` — the index is live; **do NOT run `ast-index update`**. Fall back to `Grep` only when the search is genuinely free-text (comments, log strings, error messages, non-code files).

## Project Overview
- **Name:** Mobile_Android_OnexBet
- **Type:** Large multi-module Android application (betting)
- **Language:** Kotlin (Java only if explicitly requested)
- **Build:** Groovy-based Gradle (`build.gradle`, NOT Kotlin DSL)

## Tech Stack
- **UI:** Jetpack Compose + Material 3 (legacy XML in some modules)
- **Architecture:** Clean Architecture + UDF (Unidirectional Data Flow)
- **DI:** Dagger 2 — project default for ALL feature/module DI. Write Dagger 2 for normal feature work. ViewModels are created via `udfViewModel(...)` with a Dagger `ViewModelFactory` (see `xbet-viewmodel`), NOT via `koinInject()`. (A Dagger → Koin migration runs as a separate refactoring track; it does not change how regular feature code is written — follow the module's existing Dagger 2 DI.)
- **Async:** Coroutines + Flow
- **Navigation:** Cicerone (custom XScreen/XDialog via BaseXPlatformScreen)
- **Testing:** JUnit 5, MockK, FlowTestResultHandler

## Module Structure
- `:app` — application shell, top-level wiring
- `:feature:<name>` — feature modules (often split into `api`/`impl`)
- `:core:<name>` — shared core modules (network, navigation, ui_core, viewmodel)
- `:uikit` / `:uikit_sport` — Compose design system components

## Key Architecture Patterns
- **ViewModel:** `UdfBaseViewModel<Action, UiState, SideEffect, State>` from `:core:viewmodel`
- **State:** immutable data class, updated only via `updateState { copy(...) }`
- **Actions:** sealed interface with `User` (UI events) and `Internal` (system events)
- **SideEffects:** one-off events (navigation, toasts) via `postSideEffect()`
- **Delegates:** `UdfDelegate` for composable sub-state management

## Feature Module Packaging

**Layer directories** (`data/` / `domain/` / `presentation/` / `di/` / `navigation/`) are split into **sub-directories grouped by entity type** — one entity per file in its matching sub-directory. Do not dump all UseCases / Repositories / Models into a single flat layer folder.

```
feature/<name>/
├── data/                    # (only in impl, see "Feature Module Structure" below)
│   ├── repository/          # *RepositoryImpl
│   ├── datasource/          # remote/local data sources
│   ├── model/               # *DataModel / DTOs
│   └── mapper/              # data → domain mappers
├── domain/
│   ├── usecase/             # use cases
│   ├── scenario/            # multi-step scenarios
│   ├── repository/          # repository interfaces (if exposed)
│   └── model/               # domain models (*Model)
├── presentation/
│   ├── viewmodel/           # UdfBaseViewModel subclasses
│   ├── action/              # Action sealed hierarchies (User / Internal)
│   ├── state/               # State data classes
│   ├── sideeffect/          # SideEffect sealed hierarchies
│   ├── uistate/             # UiState + mappers from State
│   ├── delegate/            # UdfDelegate implementations
│   ├── adapter/             # content adapters if applicable
│   └── ui/                  # Compose screens / Fragments
├── di/                      # Dagger components, modules, factories
└── navigation/              # screen factories (XScreen/XDialog via BaseXPlatformScreen)
```

**Rule:** every new entity (use case, repository, mapper, delegate, model, etc.) goes into its own sub-directory within its layer. A new use case → `domain/usecase/<Name>UseCase.kt`; a new delegate → `presentation/delegate/<Name>Delegate.kt`.

**Exception — "main entity of the layer"** may live **directly in the layer root** (no sub-directory), because it's canonical for that slice and typically unique per feature:
| Layer | Main entity (root of layer) | Everything else (sub-directory) |
|---|---|---|
| `data/` | `<Name>RepositoryImpl.kt` | `datasource/`, `model/`, `mapper/` |
| `domain/` | *(none — all entities are typed: use cases, scenarios, models, repo interfaces)* | `usecase/`, `scenario/`, `repository/`, `model/` |
| `presentation/` | `<Name>ViewModel.kt` | `action/`, `state/`, `sideeffect/`, `uistate/`, `mapper/`, `delegate/`, `adapter/`, `ui/` |
| `di/` | `<Name>Component.kt` / `<Name>Module.kt` (main Dagger component/module) | submodules/, factories/, qualifiers/ if many |
| `navigation/` | `<Name>Screen.kt` (main screen factory) | nested screens/, dialogs/, params/ if many |

If there is more than one candidate for the "main entity" role (e.g. several RepositoryImpls in one feature), put all of them into the corresponding sub-directory — the root is reserved for single canonical entries.

## Team Roles
- **@Architect** — module structure, API contracts, DI graph, navigation
- **@AndroidDev** — Kotlin business logic, Clean Architecture layers, ViewModel
- **@UIDev** — Jetpack Compose, screens, components, animations, theme
- **@BusinessAnalyst** — requirements, user stories, acceptance criteria, analytics
- **@TextWriter** — UX copy, strings.xml, localization, documentation
- **@Designer** — UX flows, wireframes, Figma/Pencil, design system
- **@Reviewer** — code review, UDF compliance, SOLID, performance
- **@QA** — tests (only when explicitly requested)
- **@BackendIntegrator** — API client, DTOs, error handling (only when explicitly requested)
- **@DevOps** — Gradle, CI/CD (only when explicitly requested)

## Project Docs Reference
Always consult these files for the full ruleset (do not duplicate rules in agents):
- `/Users/Victor/work/CLAUDE.md` — global coding rules (naming, types, functions, data, classes, exceptions), Android-specific rules (Architecture, DI, Testing), Build commands and packaging, Important project notes
- UDF pattern details: skill `xbet-udf-architecture`
- Reference modules: skill `xbet-reference-modules`

## Code Style (Project-Specific — supplement to CLAUDE.md)
- **Visibility — MANDATORY rule:** every declaration (class / interface / object / function / property / constructor / type alias) must be classified by its cross-module reach, and the modifier chosen accordingly:
  - **`public`** — ONLY if the declaration is consumed outside its own Gradle module (i.e. it is part of the module's `api` contract, used by another feature / by `app` / by a `:core:*` consumer).
  - **`internal`** — REQUIRED if the declaration is consumed only within its own module. No exceptions. This includes: ViewModels, Delegates, State / UiState / Action / SideEffect hierarchies, mappers, impl classes, Dagger modules/components living in `impl`, private-looking helpers, Composable screens/components defined in feature `impl`, etc.
  - **`private`** — when the declaration is used only inside the same file/class (normal Kotlin rule, not module-related).
  - Practical check: if the symbol is imported from another Gradle module, it MUST be `public`; otherwise it MUST be `internal`. Drop the default `public` modifier anywhere it shouldn't apply — unmarked Kotlin declarations are `public` by default, which is the most common violation.
  - Examples:
    - ✅ `internal class SomeViewModel : UdfBaseViewModel<…>` (consumed only inside the feature impl)
    - ✅ `interface SomeScreenFactory { fun getScreen(…): Screen }` in `feature/<name>/api` → stays `public` (crosses module boundary)
    - ❌ `class SomeMapper` inside `impl` → must be `internal class SomeMapper`
    - ❌ `fun Modifier.clickableWithRippleEffect(…)` inside a feature module → must be `internal` unless it is in `uikit` / design-system module
- **Imports:** full imports (no star). Order per `tools/codeStyle.xml`. Right margin 120
- **Reformat:** reformat all changed/new code
- **Comments:** English. Keep existing unless wrong
- **Sealed hierarchies:** prefer `sealed interface` with `data object` / `data class` / `value class`
  - `@Immutable` on action/state interfaces where applicable
  - Single-value wrappers: `@JvmInline value class`
- **DI:** Dagger 2 (project default) + constructor injection. ViewModels: `udfViewModel(viewModelKey, viewModelFactory)` with a Dagger `ViewModelFactory` (see `xbet-viewmodel`). A Dagger → Koin migration runs separately; normal feature code stays Dagger 2
- **Avoid `object` (singleton declarations):** use `object` only as a last resort or when the user explicitly asks. Allowed exceptions: `data object` inside a `sealed interface` hierarchy, `companion object { fun empty() }` for presentation-layer models (State / UiState / UiModel — per CLAUDE.md). Prefer classes with DI instead of standalone `object`s.
- **Lambda parameters — always named, never implicit `it`:** give every lambda parameter an explicit meaningful name, including single-parameter lambdas.
  - ✅ `onValueChange = { newValue -> … }`, `items.map { item -> item.id }`, `flow.collect { state -> … }`
  - ❌ `onValueChange = { … }` (relies on `it`), `items.map { it.id }`, `flow.collect { … }`
- **Multi-part functions — split across files:**
  - **Composables:** if a `@Composable` screen or component is composed of several sub-composables, extract every sub-composable into its own file inside the `presentation/ui/` directory of the feature. Group related sub-composables using nested sub-directories under `ui/` when a screen has many parts (e.g. `presentation/ui/betslip/header/HeaderBar.kt`, `presentation/ui/betslip/header/HeaderOdds.kt`).
  - **Mappers:** if a mapper delegates to several other mapper functions, extract every mapper into its own file inside the corresponding `mapper/` sub-directory (`data/mapper/` or `presentation/mapper/`).
  - **Preview providers:** each `PreviewParameterProvider` lives in its own file next to the composable it previews (same `ui/` sub-directory).

## Feature Module Structure — with `api` / `impl` split

Same sub-directory-per-entity rule applies inside each layer.

```
feature/<name>/api/                 # public contracts
  ├── di/                           # public DI contracts
  ├── domain/
  │   ├── usecase/                  # use case interfaces
  │   ├── repository/               # repository interfaces (if exposed)
  │   └── model/                    # domain models (*Model)
  ├── navigation/                   # screen factories, nav params
  └── presentation/
      └── model/                    # presentation models (*UiModel) if needed

feature/<name>/impl/                # implementation
  ├── data/
  │   ├── repository/               # *RepositoryImpl
  │   ├── datasource/
  │   ├── model/                    # *DataModel / DTOs
  │   └── mapper/
  ├── di/                           # Dagger components, modules, factories
  ├── domain/
  │   ├── usecase/                  # use case impl
  │   └── scenario/
  └── presentation/
      ├── viewmodel/
      ├── action/ state/ sideeffect/ uistate/   # UDF sealed hierarchies
      ├── mapper/                   # State → UiState, domain → presentation
      ├── delegate/                 # UdfDelegate implementations
      ├── adapter/                  # content adapters
      └── ui/                       # Compose screens / Fragments
```

## krozov-ai-tools — Slash Commands Reference

| Command | When to Use | Typical agent |
|---|---|---|
| `/check-deps` | Scan project dependencies for available updates | architect, kotlin, planner |
| `/latest-version <groupId:artifactId>` | Find latest stable version of a Maven artifact | architect, kotlin, planner |
| `/dependency-changes` | Changelog/release notes between two versions of a dependency | kotlin |
| `/code-migration` | Safe library migration (e.g. RxJava→Coroutines, Java→Kotlin, Glide→Coil) | architect, kotlin, planner |
| `/implement-task` | Full dev cycle: worktree → code → draft PR → quality loop → merge | architect, planner |
| `/prepare-for-pr` | Quality loop before PR: build → simplify → self-review → lint/tests | planner, review |
| `/create-pr` | Create PR/MR on GitHub/GitLab with commit analysis, labels, reviewers | planner, review, writer |
| `/pr-drive-to-merge` | Drive an open PR to merge: monitor CI, respond to review comments | review |
| `/generate-test-plan` | Structured test plan document (risk areas, test cases P0-P3, edge cases) | ba, review |
