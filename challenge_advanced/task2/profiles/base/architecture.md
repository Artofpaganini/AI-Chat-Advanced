# Профиль: Architecture (проектирование эпика/крупной задачи) — base

> Base-тюнинг универсального flow. **Контекст base — кросс-платформа (Android/KMM/Backend), generic-агенты; если проект окажется реальным xbet/alva — переключиться на их roster.**
> Стек/сабагенты — `base/roster.md`; общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md` (не дублировать).
> **Направление стека (Android / KMM+CMP / Backend) выбирается на создании задачи** (шпаргалка — `base/roster.md` + глоб. CLAUDE «Стек 2026»).
> **Апстрим-профиль:** производит план (10 секций) → чейнит в исполнительный. **Не имплементация.**

## Назначение / когда активен
Спроектировать архитектуру эпика/крупной фичи ДО кода: декомпозиция модулей, DI-граф, навигация, API-контракты, ADR.
**Триггеры:** «архитектура», «спроектируй», «декомпозируй эпик», «модульная структура», «DI-граф», «API-контракт», «ADR», «как разбить».
**Примеры:** «спроектируй модуль оплаты», «архитектура нового раздела статистики», «как разложить эпик на модули».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | — *(не бывает; мелкое проектирование делает `feature`/`Plan` на месте)* | — |
| S/M | 1 фича-модуль, локальная декомпозиция | @Architect solo |
| L | фича-модуль + DI/nav/API | @Architect + консилиум (architecture / api) |
| XL | эпик / миграция / KMP-инфра с нуля | @Architect + полный консилиум (architecture / security / api / devops) + SubLead |

## Стадии (DAG)
`research → module-decomposition → di/nav/api-design → adr/risks → plan`. Persistent-файл: `./swarm-report/<slug>-architecture.md` (живой источник правды).
- **research** — консилиум разных линз (architecture / security / api / devops): как устроено сейчас, ограничения, зависимости.
- **module-decomposition** — разбить на модули/слои, нарисовать **ASCII-граф зависимостей**, флагать циклы.
- **di/nav/api-design** — DI-граф (по направлению: Hilt/Koin — Android, Koin — KMM, Spring/Ktor-DI — backend), навигация (deeplinks), API-контракты + модели по слою (naming из conventions).
- **adr/risks** — ADR (решение + альтернативы + обоснование), риски, допущения `[ASSUMPTION:]`.
- **plan** — roadmap с оценками задач (S/M/L/XL), open questions.
**Переходы:** линейно; из `design`/`adr` назад в `decomposition` при обнаружении цикла/конфликта.
Перед сменой стадии: `Переход: <текущая> → <следующая>`.

## Сабагенты по стадиям
| Стадия | Роль → агент (base) | Модель | Цель |
|---|---|---|---|
| research | @Architect (`Plan`) + консилиум (architecture / security / api / devops, `Explore`) | opus | текущее устройство + ограничения — параллельно, разные линзы |
| module-decomposition | @Architect (`Plan`) | opus | модули/слои + ASCII-граф зависимостей, флаг циклов |
| di/nav/api-design | @Architect (`Plan`) | opus | DI-граф, навигация, API-контракты + модели |
| adr/risks + plan | @Architect (`Plan`) | opus | ADR, риски, roadmap с оценками |

**Base-агенты:** @Architect→`Plan`/`general-purpose` · @Dev/@UIDev/@BackendDev/@QA→`general-purpose` · @Reviewer→`general-purpose` (+skill `superpowers:requesting-code-review`) · @Researcher→`Explore` · @DevOps→Bash в сессии. Роль+стек+I/O-контракт — в промпте агента.

## MCP / Skills (обязательные)
`ast-index` (граф модулей / зависимости / callers / структура — не `update`) · `Context7`/DeepWiki (паттерны/доки, не по памяти) ·
`./conventions.md` (модели/слои/visibility/UDF — single source; base без project-context-скилла) · `compose-principles` (если UI-направление) · `team-lead-orchestration` · `koin-migration:di-migration` (если DI-миграция).

## Output — 10 секций (обязательная структура плана)
`Overview` · `Module Structure` (**ASCII-граф зависимостей**) · `API & Models` · `DI` · `Navigation` ·
`Architecture (UDF)` · `Build` (билд направления, напр. `./gradlew :androidApp:assembleDevDebug` для KMM) · `Roadmap (S/M/L/XL)` · `Risks` · `Open Questions`.

## MUST (обязан)
- **Рисовать ASCII-граф зависимостей** модулей (кто на кого ссылается).
- **Обосновывать каждое решение** (ADR: почему это, а не альтернатива — минимум 2-3 варианта).
- **Флагать циклические зависимости** явно (не прятать).
- Помечать допущения `[ASSUMPTION:]`; оценки задач по шкале **S/M/L/XL**.
- Модели/слои/visibility — по `./conventions.md` (naming, `internal`-по-умолчанию).

## MUST NOT (нельзя)
- Писать имплементацию (только контракты / сигнатуры / скелеты).
- Оставлять цикл зависимостей без флага.
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
`architecture → refactor` (реструктуризация) / `architecture → migration` (DI/инфра-миграция).
План-файл (10 секций) передаётся как вход в промпт исполнителя.
