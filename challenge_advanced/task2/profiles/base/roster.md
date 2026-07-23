# Roster - base (кросс-платформа: Android + KMM + Backend)

**Контекст:** дефолтный roster для проектов БЕЗ собственной команды сабагентов (напр. новый KMM-проект
`AI-Chat-Advanced`, бэкенд-сервис). Покрывает все три направления; конкретный стек - из `./conventions.md`
(«Стек по платформам 2026» в глобальном CLAUDE.md) + определяется на создании задачи.

## Роль -> сабагент (generic)
Спец-агентов xbet-*/alva- здесь нет - используем **`general-purpose`** с чётким I/O-контрактом и указанием
роли/стека в промпте (либо `Explore` для read-only, `Plan` для проектирования).

| Роль | subagent_type | Зона |
|---|---|---|
| @Architect | `Plan` / `general-purpose` | архитектура, декомпозиция, DI-граф, ADR |
| @Dev | `general-purpose` | реализация (Android / KMM shared / Backend - по задаче) |
| @UIDev | `general-purpose` | Compose (Android/CMP) UI |
| @BackendDev | `general-purpose` | Ktor/Spring, API, персистентность |
| @Reviewer | `general-purpose` (+ skill `superpowers:requesting-code-review`) | ревью |
| @Researcher | `Explore` | read-only разведка кодовой базы |
| @QA | `general-purpose` | тесты (opt-in) |
| @DevOps | *Bash в сессии* | Gradle/CI/CD, Docker |

## Стек по направлению (краткая шпаргалка - детали в глобальном CLAUDE.md)
- **Android:** Kotlin 2.x · Compose+Material3 · AGP 8/9 · Hilt/Koin · Retrofit/Ktor · Room+DataStore · MVI/UDF.
- **KMM+CMP:** KMP · Compose MP (iOS stable) · Ktor+serialization · Koin · SQLDelight/Room-KMP · Nav3/Decompose · UDF.
- **Backend (Kotlin/Java):** Kotlin 2.x/Java 21 · Spring Boot 3 / Ktor server · Exposed/JPA/jOOQ · PostgreSQL · Flyway · Testcontainers.

Skills: `compose-principles` (для Compose-задач) · `team-lead-orchestration` · любые релевантные (`navigation-3`,
`material-3`, `edge-to-edge`, `koin-migration:di-migration`, `agp-9-upgrade`, `r8-analyzer`).
Если проект окажется реальным xbet/alva - переключиться на их roster.

**Примеры кода (хорошо / плохо / шаблон, под каждое направление Android/KMM/Backend) - `./conventions.md`.**
