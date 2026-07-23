# Roster - alva (KMM + Compose Multiplatform)

**Контекст:** KMP · Ktor · kotlinx.serialization · Coroutines · DataStore · **Koin** · Napier. UI (обе платформы,
дефолт): **Compose Multiplatform** (shared) · Material 3 · **Compose Navigation 3** · UDF со **Event**. iOS-натив
(SwiftUI) - только когда явно нужно. Build: `./gradlew :androidApp:assembleDebug` (+ Xcode для iOS).
Ресурсы `composeResources/`. Тесты **opt-in**. Gradle **Kotlin DSL + convention-plugins + version catalog**.
MCP-доки: **DeepWiki**. Правила: `Alva/CLAUDE.md` + skill `alva-project-context`. Шаг «identify platforms» - ВКЛючить (platform parity).

## Роль -> сабагент
| Роль | subagent_type | Зона |
|---|---|---|
| @Architect | `alva-planner-expert` (+ `alva-architect-expert` знания) | KMP-архитектура, shared/platform, DI, expect/actual |
| @KmpDev | `alva-kotlin-expert` | shared-логика, data/domain, VM, expect/actual, Ktor |
| @AndroidUiDev | `alva-android-ui-expert` | **shared Compose UI** (служит Android И iOS), `Alva`-префикс |
| @IosUiDev | `alva-ios-ui-expert` | **только натив iOS** (SwiftUI/bridges), когда явно нужно |
| @BackendDev | `alva-kotlin-expert` | Ktor client в shared, ResponseModel, mapping |
| @Reviewer | `alva-review-expert` | ревью обеих платформ против конвенций |
| @BusinessAnalyst | `alva-ba-expert` | требования, baby-care домен, platform-classification |
| @Designer | `alva-designer-expert` | UX-flow, Figma/Pencil, кросс-платформенная дизайн-система |
| @TextWriter | `alva-writer-expert` | UX-copy, `composeResources` strings, локализация |
| @ProjectManager | `alva-project-manager-expert` | задачи (Jira/Linear/GH), Epic->vertical-slice, спринты, риски |
| @QA | *general-purpose / solo* | kotlin.test, Turbine, Compose Testing (**opt-in**) |
| @DevOps | *Bash в сессии Team Lead* | Gradle KMP, CocoaPods/SPM, CI/CD |

XS session-only: `Explore` · `alva-planner-expert` · `alva-android-ui-expert` · `alva-kotlin-expert` · `alva-review-expert` (`alva-ios-ui-expert` - только iOS).
Skills: `alva-udf-architecture` (Event) · `alva-viewmodel` · `alva-project-context` · `navigation-3` · `compose-principles` · `ux-writer-core`.
Правило UI: обычный экран = **один shared Compose** (@AndroidUiDev), НЕ плодить @IosUiDev параллельно.
**Примеры кода (хорошо / плохо / шаблон, alva-специфика) - `./conventions.md`.**
