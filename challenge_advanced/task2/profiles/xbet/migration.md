# Профиль: migration — xbet

> Контекст **xbet** (`Mobile_Android_OnexBet`); также обслуживает twin **xbet1** (`own_xbet`).
> Android-only · Build `./gradlew assembleBetaDebug` · **Cicerone `XPlatformRouter`** (не менять) · Groovy Gradle.
> **Типовая xbet-миграция: Dagger 2 → Koin** (skill `koin-migration:di-migration`).
> Стек/сабагенты — `roster.md`. Общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` и `./conventions.md` (не дублировать).

## Назначение / когда активен
Перевод кодовой базы на другой фреймворк / версию / паттерн **батчами**. Конкретный тип резолвится на
создании задачи. **Основной кейс xbet — Dagger→Koin**; прочие: AGP-upgrade, XML→Compose, Billing-upgrade, Koin-DSL→Safe-DSL.
**Триггеры:** «мигрируй», «переведи на», «обнови до версии», «замени X на Y», «Dagger→Koin».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | 1 модуль/класс на новый паттерн | session-only: `xbet-kotlin-expert` |
| S | несколько классов, 1 батч | `xbet-kotlin-expert` → gate |
| M | фича целиком, 2-4 батча | `xbet-planner-expert` (audit) → `xbet-kotlin-expert` → gate ×N |
| L | десятки модулей | `xbet-planner-expert` → 2-3 `xbet-kotlin-expert` на disjoint-батчах → gate ×N, SubLead |
| XL | проект-wide (сотни точек) | full team + SubLead, worktree-параллель, периодический smoke |

## Стадии (DAG)
`audit → plan → migrate-batch → gate → (repeat) → report → done`.
`audit` — поверхность миграции (точки, кластеры, зависимости). `plan` — нарезка на изолированные disjoint-батчи.
`migrate-batch → gate` **после КАЖДОГО батча** → `repeat`, пока остаток не 0. Красный gate → фикс внутри
батча, дальше не двигаться. Persistent: `./swarm-report/<slug>-migration.md` (поверхность, батчи, прогресс `[x]`,
счётчик остатка) — перечитывать перед каждым батчем.

## Сабагенты по стадиям
| Стадия | Роль (subagent) | Модель | Цель |
|---|---|---|---|
| audit | `xbet-planner-expert` + ast-index | Opus | посчитать площадь, кластеризовать, выявить loop/shared-типы, риск-порядок |
| plan | `xbet-planner-expert` | Opus | нарезать на disjoint-батчи (~30-40 точек), порядок bottom-up |
| migrate-batch | `xbet-kotlin-expert` (2-3 на disjoint-батчах) | Sonnet | механический перевод батча по skill-рецепту |
| gate | Bash (@DevOps) + `xbet-review-expert` | Sonnet | `assembleBetaDebug` + verify (DI-граф) после КАЖДОГО батча; аудит регистраций |
| report | оркестратор | — | поверхность / прогресс / остаток / гейт-результаты |

## MCP / Skills (обязательные)
**`koin-migration:di-migration`** (Dagger→Koin — рецепты, compile-safety, KOIN-D001) · `agp-9-upgrade` (AGP) ·
`migrate-xml-views-to-jetpack-compose` (XML→Compose) · `play-billing-library-version-upgrade` — **резолвится
по типу задачи**. `ast-index` (площадь/usages) · **Context7** (целевой API/версия) · caveman.
Skills: `xbet-project-context` · `xbet-reference-modules` · `team-lead-orchestration`.

## MUST (обязан)
- Гейт (`assembleBetaDebug` + verify) **после КАЖДОГО батча**; красный гейт → стоп, фикс в батче, только потом дальше.
- Текущая ветка + малые атомарные откатываемые коммиты (по просьбе) / бэкап-точки перед батчем.
- DI-миграции — через skill `koin-migration:di-migration` (Dagger→Koin: `@ComponentScan` = narrowest data subpackage).
- Аудит declared-vs-registered каждые ~5 батчей (потерянная регистрация = зелёный build + runtime NoDefinitionFound).

## MUST NOT (нельзя)
- Big-bang (весь проект одним заходом) — только батчи.
- Пропускать / откладывать гейт («наверстаю потом»).
- Смешивать миграцию с рефактором / фичами в одном батче.
- Менять классы Cicerone / `XPlatformRouter`.
- Удалять «мёртвый» код под видом миграции без разрешения (dead code мигрируется наравне).

## Формат ответа
Поверхность (N точек, кластеры) · батч-план · прогресс (сделано / осталось) · гейт-результат каждого батча
(`assembleBetaDebug` + verify) · остаток до 0. Код — только если load-bearing (рецепт/конфликт).

**Маркировка прогресса — обязательна на каждом шаге task execution:**
- **Старт шага:** `▶️ **ШАГ <n>/<N> · <стадия>** — <название шага>`
- **Задача шага:** `🎯 **Задача:** <что именно делаем — одна строка>`
- **Итог шага:** `✅ **Итог:** <главная мысль>` · провал — `❌ **Провал:** <что сломалось + где>` · частично — `⚠️ **Частично:** <что осталось>`
- **Переход стадии:** `🔀 **Переход:** <стадия> → <стадия>` · чейнинг — `⛓️ **Chaining:** <profile> → <profile>`

Каждая метка — отдельной строкой, иконка + **жирный** лейбл, не сливать с прозой. Между шагами — `---`.
Без маркировки шаг считается незакрытым.

## Chaining (если апстрим)
**Downstream от `architecture → migration`.** На входе — целевой паттерн/версия и порядок из архитектурного
артефакта. Сам не апстрим: терминал `done`.
