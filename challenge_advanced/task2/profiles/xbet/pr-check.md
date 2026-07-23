# Профиль: pr-check — xbet (L1 код-тесты + L2 smoke → единый отчёт)

> Контекст **xbet** (`Mobile_Android_OnexBet`); также обслуживает twin **xbet1** (`own_xbet`).
> Android-only · Build `./gradlew assembleBetaDebug` · тесты **opt-in** (JUnit5+MockK+FlowTestResultHandler+verifyRouter) · smoke через claude-in-mobile/adb.
> Стек/сабагенты — `roster.md`. Общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md`.

## Назначение / когда активен
После PR / перед merge / после деплоя фичи — прогнать оба уровня тестов и собрать единый отчёт.
Триггеры: «прогони тесты и smoke», «проверь PR», «CI-check», «я задеплоил фичу — прогони всё заново».

## Размер (XS→XL) → масштаб команды
| Размер | Пример | Команда |
|---|---|---|
| XS/S | 1 модуль изменён | session: `xbet-tester-expert` (тесты) + adb/claude-in-mobile (smoke) |
| M | фича 1-2 экрана | `xbet-tester-expert` → smoke-runner → `xbet-review-expert` агрегирует |
| L/XL | эпик / много модулей | консилиум по слоям + параллельные smoke-сценарии |

## Стадии (DAG)
`gather-diff → L1 (unit/integration изменённых модулей) → L2 (smoke-сценарии через MCP/adb) → aggregate → verdict`
Переходы: L1↔L2 независимы (можно параллельно); при падении → `Chaining: pr-check → bug-fix` (или `incident` для прод).
Persistent: `./swarm-report/<slug>-pr-check.md` + скрины smoke в `smoke/shots/`.

## Сабагенты по стадиям
| Стадия | Роль (subagent) | Модель | Цель |
|---|---|---|---|
| gather-diff | `xbet-review-expert` / session | sonnet | что изменил PR, какие модули/экраны затронуты |
| L1 tests | `xbet-tester-expert` | sonnet | запустить unit/integration тесты затронутых модулей, зелёные |
| L2 smoke | Bash (@DevOps, adb) или claude-in-mobile MCP | sonnet | протыкать сценарии, скрин на каждом шаге, PASS/FAIL |
| aggregate | `xbet-review-expert` | sonnet | единый отчёт L1+L2 |

## MCP / Skills (обязательные)
`claude-in-mobile` (мобилка) или **adb** по эмулятору · ast-index · Sentry ·
профиль `test` (L1 тест-конвенции: FlowTestResultHandler/verifyRouter) · `xbet-testing` · `smoke/scenarios.md` проекта.

## MUST (обязан)
- Прогнать **оба** уровня. L1 — реально запустить тест-таск (не «на глаз»). L2 — реальные тапы + **скрин на каждом шаге**.
- Единый отчёт: L1 (N tests passed/failed) + L2 (сценарии PASS/FAIL + скрины) + итоговый вердикт.
- При падении — указать **где** проблема (файл/строка для L1; шаг/экран + logcat FATAL для L2).

## MUST NOT (нельзя)
- Мержить/деплоить на красном (L1 fail или L2 FAIL).
- Пропускать smoke «потому что тесты зелёные» (и наоборот).
- Заявлять «прошло» без реального прогона.

## Формат ответа
```

**Маркировка прогресса — обязательна на каждом шаге task execution:**
- **Старт шага:** `▶️ **ШАГ <n>/<N> · <стадия>** — <название шага>`
- **Задача шага:** `🎯 **Задача:** <что именно делаем — одна строка>`
- **Итог шага:** `✅ **Итог:** <главная мысль>` · провал — `❌ **Провал:** <что сломалось + где>` · частично — `⚠️ **Частично:** <что осталось>`
- **Переход стадии:** `🔀 **Переход:** <стадия> → <стадия>` · чейнинг — `⛓️ **Chaining:** <profile> → <profile>`

Каждая метка — отдельной строкой, иконка + **жирный** лейбл, не сливать с прозой. Между шагами — `---`.
Без маркировки шаг считается незакрытым.

## PR-Check отчёт
L1 (код): N тестов, N passed, N failed [файл:строка если fail]
L2 (smoke): S1..S5 — PASS/FAIL, скрины shots/*.png [шаг+диагноз если fail]
Вердикт: MERGE-READY / BLOCKED (причина)
```

## Chaining / вариация «задеплоил фичу»
- Запрос «я задеплоил новую фичу — обнови smoke и прогони всё заново»: сперва **обновить `smoke/scenarios.md`**
  (добавить шаги под новую фичу — новые экраны/действия), затем полный прогон L1+L2 и единый отчёт.
- Любой FAIL → `Chaining: pr-check → bug-fix` (прод → `incident`), передать диагноз/скрин/стек.
