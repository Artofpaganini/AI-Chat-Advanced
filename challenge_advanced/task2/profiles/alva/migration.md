# Профиль: migration — alva (KMM+CMP baby-care)

> Контекст **alva** (Kotlin Multiplatform + Compose Multiplatform, baby-care). Роли → сабагенты из `alva/roster.md`;
> общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md` (не дублировать).
> Стек: KMP · CMP (shared обе платформы) · Koin · Compose Navigation 3 · UDF со **Event** · `Alva`-префикс DS ·
> Kotlin DSL + convention-plugins + version catalog · `composeResources/` · доки — **DeepWiki**. Build: `./gradlew :androidApp:assembleDebug` (+ Xcode iOS).

## Назначение / когда активен
Перевод кодовой базы на другой фреймворк / версию / паттерн **батчами**. Конкретный тип резолвится на
создании задачи (пример: AGP-upgrade, Koin-DSL→Safe-DSL, Navigation→Compose Nav 3, версия-catalog bump, expect/actual-рефактор).
**Триггеры:** «мигрируй», «переведи на», «обнови до версии», «замени X на Y».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | 1 модуль/класс на новый паттерн | session-only: `alva-kotlin-expert` |
| S | несколько классов, 1 батч | `alva-kotlin-expert` → gate |
| M | фича целиком, 2-4 батча | `alva-planner-expert` (audit) → `alva-kotlin-expert` → gate ×N |
| L | десятки модулей | `alva-planner-expert` → 2-3 `alva-kotlin-expert` на disjoint-батчах → gate ×N, SubLead |
| XL | проект-wide (сотни точек) | full team + SubLead, worktree-параллель, периодический smoke |

## Стадии (DAG)
`audit → plan → migrate-batch → gate → (repeat) → report → done`.
`audit` — поверхность миграции (точки, кластеры, зависимости, **затронутые платформы commonMain/androidMain/iosMain**). `plan` — нарезка на изолированные disjoint-батчи.
`migrate-batch → gate` **после КАЖДОГО батча** → `repeat`, пока остаток не 0. Красный gate → фикс внутри
батча, дальше не двигаться. Persistent: `./swarm-report/<slug>-migration.md` (поверхность, батчи, прогресс `[x]`,
счётчик остатка) — перечитывать перед каждым батчем.

## Сабагенты по стадиям
| Стадия | Роль → сабагент | Модель | Цель |
|---|---|---|---|
| audit | @Architect `alva-planner-expert` + ast-index | Opus | посчитать площадь, кластеризовать, выявить loop/shared-типы/expect-actual, риск-порядок |
| plan | @Architect `alva-planner-expert` | Opus | нарезать на disjoint-батчи (~30-40 точек), порядок bottom-up |
| migrate-batch | @Dev `alva-kotlin-expert` (2-3 на disjoint-батчах) | Sonnet | механический перевод батча по skill-рецепту |
| gate | @DevOps (Bash) + @Reviewer `alva-review-expert` | Sonnet | build (`:androidApp:assembleDebug`, iOS при shared) + verify после КАЖДОГО батча; аудит регистраций |
| report | оркестратор | — | поверхность / прогресс / остаток / гейт-результаты |

## MCP / Skills (обязательные)
`agp-9-upgrade` (AGP) · `koin-migration:di-migration` (Koin DSL→Safe-DSL / версии) · `navigation-3` (Nav-миграция) ·
`play-billing-library-version-upgrade` — **резолвится по типу задачи**. `ast-index` (площадь/usages) · **DeepWiki** (целевой API/версия KMP) · caveman.
Skills: `alva-project-context` · `team-lead-orchestration`.

## MUST (обязан)
- Гейт (build + verify) **после КАЖДОГО батча**; красный гейт → стоп, фикс в батче, только потом дальше.
- **Проверять обе платформы** при миграции shared-кода (parity); build `:androidApp:assembleDebug` + iOS/Xcode при затронутом commonMain.
- Текущая ветка + малые атомарные откатываемые коммиты (по просьбе) / бэкап-точки перед батчем.
- Koin-миграции — через skill `koin-migration:di-migration`.
- Аудит declared-vs-registered каждые ~5 батчей (потерянная регистрация = зелёный build + runtime-краш).

## MUST NOT (нельзя)
- Big-bang (весь проект одним заходом) — только батчи.
- Пропускать / откладывать гейт («наверстаю потом»).
- Смешивать миграцию с рефактором / фичами в одном батче.
- Ломать platform parity; удалять «мёртвый» код под видом миграции без разрешения (dead code мигрируется наравне).

## Формат ответа
Поверхность (N точек, кластеры, платформы) · батч-план · прогресс (сделано / осталось) · гейт-результат каждого батча
(build + verify) · остаток до 0. Код — только если load-bearing (рецепт/конфликт).

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
