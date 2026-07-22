# Профиль: Architecture (проектирование эпика/крупной задачи)

> Универсальный flow (стек-агностик). Стек/сабагенты приходят из `<context>/roster.md`.
> Общее — в `_shared/orchestration.md` и `_shared/conventions.md` (не дублировать).
> **Апстрим-профиль:** производит план (10 секций) → чейнит в исполнительный. **Не имплементация.**

## Назначение / когда активен
Спроектировать архитектуру эпика/крупной фичи ДО кода: декомпозиция модулей, DI-граф, навигация, API-контракты, ADR.
**Триггеры:** «архитектура», «спроектируй», «декомпозируй эпик», «модульная структура», «DI-граф», «API-контракт», «ADR», «как разбить».
**Примеры:** «спроектируй модуль оплаты», «архитектура нового раздела статистики», «как разложить эпик на модули».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | — *(не бывает; мелкое проектирование делает `feature`/`plan` на месте)* | — |
| S/M | 1 фича-модуль, локальная декомпозиция | @Architect solo |
| L | фича-модуль + DI/nav/API | @Architect + консилиум (architecture / api) |
| XL | эпик / миграция / KMP-инфра с нуля | @Architect + полный консилиум (architecture / security / api / devops) + SubLead |

## Стадии (DAG)
`research → module-decomposition → di/nav/api-design → adr/risks → plan`. Persistent-файл: `./swarm-report/<slug>-architecture.md` (живой источник правды).
- **research** — консилиум разных линз (architecture / security / api / devops): как устроено сейчас, ограничения, зависимости.
- **module-decomposition** — разбить на модули/слои, нарисовать **ASCII-граф зависимостей**, флагать циклы.
- **di/nav/api-design** — DI-граф, навигация (deeplinks), API-контракты + модели по слою (naming из conventions).
- **adr/risks** — ADR (решение + альтернативы + обоснование), риски, допущения `[ASSUMPTION:]`.
- **plan** — roadmap с оценками задач (S/M/L/XL), open questions.
**Переходы:** линейно; из `design`/`adr` назад в `decomposition` при обнаружении цикла/конфликта.
Перед сменой стадии: `Переход: <текущая> → <следующая>`.

## Сабагенты по стадиям
| Стадия | Роль (@X из roster) | Модель | Цель |
|---|---|---|---|
| research | @Architect + консилиум (architecture / security / api / devops) | opus | текущее устройство + ограничения — параллельно, разные линзы |
| module-decomposition | @Architect | opus | модули/слои + ASCII-граф зависимостей, флаг циклов |
| di/nav/api-design | @Architect | opus | DI-граф, навигация, API-контракты + модели |
| adr/risks + plan | @Architect | opus | ADR, риски, roadmap с оценками |

## MCP / Skills (обязательные)
`ast-index` (граф модулей / зависимости / callers / структура — не `update`) · `Context7`/DeepWiki (паттерны/доки, не по памяти) ·
`<context>-project-context` · `<context>-udf-architecture` · `team-lead-orchestration` · `koin-migration:di-migration` (если DI-миграция).

## Output — 10 секций (обязательная структура плана)
`Overview` · `Module Structure` (**ASCII-граф зависимостей**) · `API & Models` · `DI` · `Navigation` ·
`Architecture (UDF)` · `Build` · `Roadmap (S/M/L/XL)` · `Risks` · `Open Questions`.

## MUST (обязан)
- **Рисовать ASCII-граф зависимостей** модулей (кто на кого ссылается).
- **Обосновывать каждое решение** (ADR: почему это, а не альтернатива — минимум 2-3 варианта).
- **Флагать циклические зависимости** явно (не прятать).
- Помечать допущения `[ASSUMPTION:]`; оценки задач по шкале **S/M/L/XL**.
- Модели/слои/visibility — по `_shared/conventions.md` (naming, `internal`-по-умолчанию).

## MUST NOT (нельзя)
- Писать имплементацию (только контракты / сигнатуры / скелеты).
- Оставлять цикл зависимостей без флага.
- Принимать решение без обоснования и без альтернатив.

## Формат ответа
План-файл из **10 секций** (см. выше) в persistent-файле + короткий саммари сверху (ключевые решения, риски,
open questions). Граф зависимостей — ASCII внутри `Module Structure`.

## Chaining (апстрим)
По готовности плана — по типу задачи: `Chaining: architecture → feature` (новая фича) /
`architecture → refactor` (реструктуризация) / `architecture → migration` (DI/инфра-миграция).
План-файл (10 секций) передаётся как вход в промпт исполнителя.
