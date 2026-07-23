# Профиль: architecture — xbet (проектирование эпика/крупной задачи)

> Контекст **xbet** (`Mobile_Android_OnexBet`); также обслуживает twin **xbet1** (`own_xbet`).
> Android-only · Kotlin/Compose · **Dagger 2** (+Koin-track) · **Cicerone `XPlatformRouter`** (не менять) ·
> UDF со **SideEffect** (+Delegates) · Groovy Gradle · Build `./gradlew assembleBetaDebug` · MCP-доки **Context7**.
> Стек/сабагенты — `roster.md`. Общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` и `./conventions.md` (не дублировать).
> **Апстрим-профиль:** производит план (10 секций) → чейнит в исполнительный. **Не имплементация.**

## Назначение / когда активен
Спроектировать архитектуру эпика/крупной фичи ДО кода: декомпозиция модулей, Dagger-граф, навигация (Cicerone), API-контракты, ADR.
**Триггеры:** «архитектура», «спроектируй», «декомпозируй эпик», «модульная структура», «DI-граф», «API-контракт», «ADR», «как разбить».
**Примеры:** «спроектируй модуль оплаты», «архитектура нового раздела статистики», «как разложить эпик на модули».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | — *(не бывает; мелкое проектирование делает `feature`/`plan` на месте)* | — |
| S/M | 1 фича-модуль, локальная декомпозиция | `xbet-planner-expert` (+`xbet-architect-expert` знания) solo |
| L | фича-модуль + DI/nav/API | `xbet-planner-expert` + консилиум (architecture / api) |
| XL | эпик / миграция / инфра с нуля | `xbet-planner-expert` + полный консилиум (architecture / security / api / devops) + SubLead |

## Стадии (DAG)
`research → module-decomposition → di/nav/api-design → adr/risks → plan`. Persistent-файл: `./swarm-report/<slug>-architecture.md` (живой источник правды).
- **research** — консилиум разных линз (architecture / security / api / devops): как устроено сейчас, ограничения, зависимости.
- **module-decomposition** — разбить на модули/слои, нарисовать **ASCII-граф зависимостей**, флагать циклы.
- **di/nav/api-design** — Dagger-граф (или Koin по треку миграции), навигация (Cicerone `XPlatformRouter`, deeplinks), API-контракты + модели по слою (naming из conventions).
- **adr/risks** — ADR (решение + альтернативы + обоснование), риски, допущения `[ASSUMPTION:]`.
- **plan** — roadmap с оценками задач (S/M/L/XL), open questions.
**Переходы:** линейно; из `design`/`adr` назад в `decomposition` при обнаружении цикла/конфликта.
Перед сменой стадии: `Переход: <текущая> → <следующая>`.

## Сабагенты по стадиям
| Стадия | Роль (subagent) | Модель | Цель |
|---|---|---|---|
| research | `xbet-planner-expert` + консилиум (architecture / security / api / devops) | opus | текущее устройство + ограничения — параллельно, разные линзы |
| module-decomposition | `xbet-planner-expert` (+`xbet-architect-expert` знания) | opus | модули/слои + ASCII-граф зависимостей, флаг циклов |
| di/nav/api-design | `xbet-planner-expert` | opus | Dagger-граф, навигация (Cicerone), API-контракты + модели |
| adr/risks + plan | `xbet-planner-expert` | opus | ADR, риски, roadmap с оценками |

## MCP / Skills (обязательные)
`ast-index` (граф модулей / зависимости / callers / структура — не `update`) · **Context7** (паттерны/доки, не по памяти) ·
`xbet-project-context` · `xbet-udf-architecture` · `xbet-navigation` · `xbet-reference-modules` · `team-lead-orchestration` · `koin-migration:di-migration` (если Dagger→Koin).

## Output — 10 секций (обязательная структура плана)
`Overview` · `Module Structure` (**ASCII-граф зависимостей**) · `API & Models` · `DI` (Dagger/Koin) · `Navigation` (Cicerone) ·
`Architecture (UDF/SideEffect)` · `Build` (`assembleBetaDebug`) · `Roadmap (S/M/L/XL)` · `Risks` · `Open Questions`.

## MUST (обязан)
- **Рисовать ASCII-граф зависимостей** модулей (кто на кого ссылается).
- **Обосновывать каждое решение** (ADR: почему это, а не альтернатива — минимум 2-3 варианта).
- **Флагать циклические зависимости** явно (не прятать).
- Помечать допущения `[ASSUMPTION:]`; оценки задач по шкале **S/M/L/XL**.
- Модели/слои/visibility — по `./conventions.md` (naming, `internal`-по-умолчанию); навигация — поверх Cicerone, классы не менять.

## MUST NOT (нельзя)
- Писать имплементацию (только контракты / сигнатуры / скелеты).
- Оставлять цикл зависимостей без флага.
- Проектировать замену классов Cicerone / `XPlatformRouter`.
- Принимать решение без обоснования и без альтернатив.

## Формат ответа
План-файл из **10 секций** (см. выше) в persistent-файле + короткий саммари сверху (ключевые решения, риски,
open questions). Граф зависимостей — ASCII внутри `Module Structure`.

**Маркировка прогресса — обязательна на каждом шаге task execution:**
- **Старт шага:** `▶️ **ШАГ <n>/<N> · <стадия>** — <название шага>`
- **Задача шага:** `🎯 **Задача:** <что именно делаем — одна строка>`
- **Итог шага:** `✅ **Итог:** <главная мысль>` · провал — `❌ **Провал:** <что сломалось + где>` · частично — `⚠️ **Частично:** <что осталось>`
- **Переход стадии:** `🔀 **Переход:** <стадия> → <стадия>` · чейнинг — `⛓️ **Chaining:** <profile> → <profile>`

Каждая метка — отдельной строкой, иконка + **жирный** лейбл, не сливать с прозой. Между шагами — `---`.
Без маркировки шаг считается незакрытым.

## Chaining (апстрим)
По готовности плана — по типу задачи: `Chaining: architecture → feature` (новая фича) /
`architecture → refactor` (реструктуризация) / `architecture → migration` (Dagger→Koin/инфра-миграция).
План-файл (10 секций) передаётся как вход в промпт исполнителя.
