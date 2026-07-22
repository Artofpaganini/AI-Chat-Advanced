# Конвенции (общий single-source; тела сабагентов ссылаются сюда)

Полные версии живут в скиллах (`<context>-project-context`, `*-udf-architecture`, `*-viewmodel`,
`compose-principles`, `ux-writer-core`). Здесь — консолидированная общая база + дельты стеков. Сабагенты
НЕ дублируют это в теле, а ссылаются на скилл + этот файл.

## Общие (кросс-стек)
- **Видимость (MANDATORY):** `internal` по умолчанию; `public` — ТОЛЬКО если символ потребляется из другого
  Gradle-модуля (`api`-контракт / экспорт в Swift). Дефолтный `public` не оставлять — частейшее нарушение.
- **StateFlow — атомарно:** `updateState { copy(...) }` / `_state.update { … }`. НИКОГДА `_state.value = …`.
- **Модели по слою:** `data` — `*RequestModel`/`*ResponseModel`/`*DataModel` (`@Serializable`); `domain` — `*Model`;
  `presentation` — `*UiModel`. Слово **«DTO» запрещено**; голые `*Request`/`*Response` без `Model` — запрещены.
- **Мапперы:** `data→domain` — top-level extension `fun XxxResponseModel.toXxxModel()` в `data/mapper/`
  (файл на исходную модель). `State→UiModel` — класс `UiMapper<State,UiModel>` в `presentation/mapper/`.
  Никакого инлайн-маппинга в репозитории/VM, никаких `XxxMapper` с набором методов.
- **UDF:** `UdfBaseViewModel<Action, UiState, State, Event/SideEffect>`; `Action` — sealed `Ui`/`Internal`;
  весь стейт в `*State`; one-off — Event/SideEffect (post/collect/handle); `withScope`+инжектнутые диспетчеры.
- **Coroutines:** structured concurrency; `launchIn`/`observeWithLifecycle`; ошибки не глотать; Mutex — только в data.
- **Kotlin:** без `!!`, без `Any` (дженерики), без magic numbers, именованные лямбда-параметры (не `it`),
  типы параметров/возврата явно, `internal`-по-умолчанию, без незапрошенных комментариев/KDoc.
- **Compose:** `Modifier` первым опциональным; порядок параметров (Modifier→data→params→onAction→content-slot);
  минимизировать recomposition; preview-driven; a11y. Детали — `compose-principles`.
- **Секреты:** только `local.properties`→`BuildConfig`/`AppConfig`/env, не хардкодить, не коммитить.

## Дельты стеков (резолвятся по контексту через roster)
| Аспект | xbet (Android) | alva (KMM+CMP) | base |
|---|---|---|---|
| DI | Dagger 2 (+Koin-миграция) | Koin | по задаче |
| Навигация | Cicerone `XPlatformRouter` (не менять классы) | Compose Navigation 3 | по задаче |
| One-off эффект | **SideEffect** (`postSideEffect`) + Delegates (`UdfDelegate`) | **Event** (`postEvent`) | по задаче |
| DS-префикс UI | `Ds` | `Alva` | по задаче |
| Gradle | Groovy | Kotlin DSL + convention-plugins + version catalog | по задаче |
| Ресурсы | `strings.xml` | `composeResources/` | по задаче |
| Тесты | JUnit5+MockK+FlowTestResultHandler+verifyRouter (opt-in) | kotlin.test+Turbine (opt-in) | по задаче |
| MCP-доки | Context7 | DeepWiki | оба |
| Платформы | Android-only (шаг «identify platforms» пропустить) | Android+iOS из shared Compose | все |
| Билд | `./gradlew assembleBetaDebug` | `./gradlew :androidApp:assembleDebug` | по проекту |

## Скиллы (single source деталей)
`<context>-project-context` (стек/структура/visibility) · `<context>-udf-architecture` · `<context>-viewmodel`
· `xbet-navigation`/`xbet-testing`/`xbet-reference-modules` (xbet) · `compose-principles` · `team-lead-orchestration`
· `ux-writer-core` · `koin-migration:di-migration` (миграции DI).
