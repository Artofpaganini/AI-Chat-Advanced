# Roster - xbet (Mobile_Android_OnexBet)

**Контекст:** Android-only большой multi-module (Kotlin · Jetpack Compose · Material 3 · **Dagger 2** ·
Coroutines/Flow · **Cicerone** (не менять) · UDF со **SideEffect**). Build: `./gradlew assembleBetaDebug`.
Ресурсы `strings.xml`. Тесты **opt-in**. Gradle **Groovy**. MCP-доки: **Context7**.
Правила: `Mobile_Android_OnexBet/CLAUDE.md` + skill `xbet-project-context`. Шаг «identify platforms» - пропустить.

## Роль -> сабагент
| Роль | subagent_type | Зона |
|---|---|---|
| @Architect | `xbet-planner-expert` (+ загружает `xbet-architect-expert` знания) | план, архитектура, DI-граф, декомпозиция |
| @AndroidDev | `xbet-kotlin-expert` | Kotlin-логика, data/domain/presentation, UseCase, VM |
| @UIDev | `xbet-compose-expert` | Compose UI, экраны, тема, Cicerone-интеграция (`Ds`-префикс) |
| @BackendIntegrator | `xbet-kotlin-expert` | Retrofit/Ktor, ResponseModel, mapping, error handling |
| @Reviewer | `xbet-review-expert` | ревью против конвенций (visibility = Critical) |
| @QA | `xbet-tester-expert` | JUnit5+MockK+FlowTestResultHandler+verifyRouter (**opt-in only**) |
| @BusinessAnalyst | `xbet-ba-expert` | требования, user stories, betting-домен |
| @Designer | `xbet-designer-expert` | UX-flow, Figma/Pencil, дизайн-система |
| @TextWriter | `xbet-writer-expert` | UX-copy, `strings.xml`, локализация |
| @DevOps | *Bash в сессии Team Lead* | Gradle/CI/CD |

XS session-only: `Explore` · `xbet-planner-expert` · `xbet-compose-expert` · `xbet-kotlin-expert` · `xbet-review-expert`.
Skills: `xbet-udf-architecture` (SideEffect+Delegates) · `xbet-viewmodel` · `xbet-navigation` · `xbet-testing` · `xbet-reference-modules` · `compose-principles`.
Частая задача: **migration** (Dagger->Koin) - skill `koin-migration:di-migration`.
**Примеры кода (хорошо / плохо / шаблон, xbet-специфика) - `./conventions.md`.**
