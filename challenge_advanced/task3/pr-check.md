# Профиль: PR-Check (L1 код-тесты + L2 smoke -> единый отчёт) - base

> Base-тюнинг универсального flow. **Контекст base - кросс-платформа (Android/KMM/Backend), generic-агенты; если проект окажется реальным xbet/alva - переключиться на их roster.**
> Стек/сабагенты - `base/roster.md`; общее - секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md`.
> **Направление стека (Android / KMM+CMP / Backend) выбирается на создании задачи** (L2-smoke: мобилка - claude-in-mobile/adb; backend - HTTP-прогон эндпоинтов).

## Назначение / когда активен
После PR / перед merge / после деплоя фичи - прогнать оба уровня тестов и собрать единый отчёт.
Триггеры: «прогони тесты и smoke», «проверь PR», «CI-check», «я задеплоил фичу - прогони всё заново».

## Размер (XS->XL) -> масштаб команды
| Размер | Пример | Команда |
|---|---|---|
| XS/S | 1 модуль изменён | session: @QA (тесты) + adb/claude-in-mobile (smoke) |
| M | фича 1-2 экрана | @QA -> smoke-runner -> @Reviewer агрегирует |
| L/XL | эпик / много модулей | консилиум по слоям + параллельные smoke-сценарии |

## Стадии (DAG)
`gather-diff -> L1 (unit/integration изменённых модулей) -> L2 (smoke-сценарии через MCP/adb/HTTP) -> aggregate -> verdict`
Переходы: L1↔L2 независимы (можно параллельно); при падении -> `Chaining: pr-check -> bug-fix` (или `incident` для прод).
Persistent: `./swarm-report/<slug>-pr-check.md` + скрины smoke в `smoke/shots/`.

## Сабагенты по стадиям
| Стадия | Роль -> агент (base) | Модель | Цель |
|---|---|---|---|
| gather-diff | @Reviewer / session (`general-purpose`) | sonnet | что изменил PR, какие модули/экраны затронуты |
| L1 tests | @QA (`general-purpose`) | sonnet | запустить unit/integration тесты затронутых модулей, зелёные |
| L2 smoke | @DevOps/session (adb/HTTP) или claude-in-mobile MCP | sonnet | протыкать сценарии, скрин на каждом шаге, PASS/FAIL |
| aggregate | @Reviewer (`general-purpose`) | sonnet | единый отчёт L1+L2 |

**Base-агенты:** @QA/@Reviewer->`general-purpose` (@Reviewer +skill `superpowers:requesting-code-review`) · @DevOps->Bash в сессии. Роль+стек+I/O-контракт - в промпте агента.

## MCP / Skills (обязательные)
`claude-in-mobile` (мобилка) или **adb** по эмулятору · для backend - HTTP/curl прогон эндпоинтов (Testcontainers по надобности) · ast-index · Sentry ·
профиль `test` (L1 тест-конвенции) · `smoke/scenarios.md` проекта.

## MUST (обязан)
- Прогнать **оба** уровня. L1 - реально запустить тест-таск (не «на глаз»). L2 - реальные тапы/запросы + **скрин на каждом шаге**.
- Единый отчёт: L1 (N tests passed/failed) + L2 (сценарии PASS/FAIL + скрины) + итоговый вердикт.
- При падении - указать **где** проблема (файл/строка для L1; шаг/экран + logcat FATAL или HTTP-статус для L2).

## MUST NOT (нельзя)
- Мержить/деплоить на красном (L1 fail или L2 FAIL).
- Пропускать smoke «потому что тесты зелёные» (и наоборот).
- Заявлять «прошло» без реального прогона.

## Формат ответа
```
## PR-Check отчёт
L1 (код): N тестов, N passed, N failed [файл:строка если fail]
L2 (smoke): S1..S5 - PASS/FAIL, скрины shots/*.png [шаг+диагноз если fail]
Вердикт: MERGE-READY / BLOCKED (причина)
```

## Chaining / вариация «задеплоил фичу»
- Запрос «я задеплоил новую фичу - обнови smoke и прогони всё заново»: сперва **обновить `smoke/scenarios.md`**
  (добавить шаги под новую фичу - новые экраны/действия/эндпоинты), затем полный прогон L1+L2 и единый отчёт.
- Любой FAIL -> `Chaining: pr-check -> bug-fix` (прод -> `incident`), передать диагноз/скрин/стек.
