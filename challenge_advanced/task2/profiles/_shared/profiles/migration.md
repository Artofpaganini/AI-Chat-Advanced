# Профиль: migration

> Универсальный flow (стек-агностик). Стек/сабагенты приходят из `<context>/roster.md`.
> Общее — в `../orchestration.md` и `../conventions.md` (не дублировать).

## Назначение / когда активен
Перевод кодовой базы на другой фреймворк / версию / паттерн **батчами**. Конкретный тип резолвится на
создании задачи (пример: Dagger→Koin, AGP-upgrade, XML→Compose, Billing-upgrade, Koin-DSL→Safe-DSL).
**Триггеры:** «мигрируй», «переведи на», «обнови до версии», «замени X на Y».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | 1 модуль/класс на новый паттерн | session-only: @Dev |
| S | несколько классов, 1 батч | @Dev → gate |
| M | фича целиком, 2-4 батча | @Architect (audit) → @Dev → gate ×N |
| L | десятки модулей | @Architect → 2-3 @Dev на disjoint-батчах → gate ×N, SubLead |
| XL | проект-wide (сотни точек) | full team + SubLead, worktree-параллель, периодический smoke |

## Стадии (DAG)
`audit → plan → migrate-batch → gate → (repeat) → report → done`.
`audit` — поверхность миграции (точки, кластеры, зависимости). `plan` — нарезка на изолированные disjoint-батчи.
`migrate-batch → gate` **после КАЖДОГО батча** → `repeat`, пока остаток не 0. Красный gate → фикс внутри
батча, дальше не двигаться. Persistent: `./swarm-report/<slug>-migration.md` (поверхность, батчи, прогресс `[x]`,
счётчик остатка) — перечитывать перед каждым батчем.

## Сабагенты по стадиям
| Стадия | Роль (@X из roster) | Модель | Цель |
|---|---|---|---|
| audit | @Architect + ast-index | Opus | посчитать площадь, кластеризовать, выявить loop/shared-типы, риск-порядок |
| plan | @Architect | Opus | нарезать на disjoint-батчи (~30-40 точек), порядок bottom-up |
| migrate-batch | @Dev (2-3 на disjoint-батчах) | Sonnet | механический перевод батча по skill-рецепту |
| gate | @DevOps (Bash) + @Reviewer | Sonnet | build + verify (напр. DI-граф) после КАЖДОГО батча; аудит регистраций |
| report | оркестратор | — | поверхность / прогресс / остаток / гейт-результаты |

## MCP / Skills (обязательные)
`koin-migration:di-migration` (DI-миграции — рецепты, compile-safety) · `agp-9-upgrade` (AGP) ·
`migrate-xml-views-to-jetpack-compose` (XML→Compose) · `play-billing-library-version-upgrade` — **резолвится
по типу задачи**. `ast-index` (площадь/usages) · `Context7`/DeepWiki (целевой API/версия) · caveman.
Skills: `<context>-project-context` · `team-lead-orchestration`.

## MUST (обязан)
- Гейт (build + verify) **после КАЖДОГО батча**; красный гейт → стоп, фикс в батче, только потом дальше.
- Текущая ветка + малые атомарные откатываемые коммиты (по просьбе) / бэкап-точки перед батчем.
- DI-миграции — через skill `koin-migration:di-migration`.
- Аудит declared-vs-registered каждые ~5 батчей (потерянная регистрация = зелёный build + runtime-краш).

## MUST NOT (нельзя)
- Big-bang (весь проект одним заходом) — только батчи.
- Пропускать / откладывать гейт («наверстаю потом»).
- Смешивать миграцию с рефактором / фичами в одном батче.
- Удалять «мёртвый» код под видом миграции без разрешения (dead code мигрируется наравне).

## Формат ответа
Поверхность (N точек, кластеры) · батч-план · прогресс (сделано / осталось) · гейт-результат каждого батча
(build + verify) · остаток до 0. Код — только если load-bearing (рецепт/конфликт).

## Chaining (если апстрим)
**Downstream от `architecture → migration`.** На входе — целевой паттерн/версия и порядок из архитектурного
артефакта. Сам не апстрим: терминал `done`.
