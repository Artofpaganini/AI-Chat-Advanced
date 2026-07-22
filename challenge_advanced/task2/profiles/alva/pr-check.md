# Профиль: PR-Check — alva (KMM+CMP baby-care) (L1 код-тесты + L2 smoke → единый отчёт)

> Контекст **alva** (KMP + CMP, baby-care). Роли → сабагенты из `alva/roster.md`. Общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md`.
> Стек: KMP · CMP (shared обе платформы) · Koin · Compose Navigation 3 · UDF со **Event** · `Alva`-префикс DS · доки — **DeepWiki**.
> Build: `./gradlew :androidApp:assembleDebug` (+ Xcode iOS). Тесты — **opt-in** (kotlin.test/Turbine).

## Назначение / когда активен
После PR / перед merge / после деплоя фичи — прогнать оба уровня тестов и собрать единый отчёт.
Триггеры: «прогони тесты и smoke», «проверь PR», «CI-check», «я задеплоил фичу — прогони всё заново».

## Размер (XS→XL) → масштаб команды
| Размер | Пример | Команда |
|---|---|---|
| XS/S | 1 модуль изменён | session: @QA `general-purpose` (тесты) + adb/claude-in-mobile (smoke) |
| M | фича 1-2 экрана | @QA → smoke-runner → `alva-review-expert` агрегирует |
| L/XL | эпик / много модулей / обе платформы | консилиум по слоям + параллельные smoke-сценарии (Android + iOS) |

## Стадии (DAG)
`gather-diff → identify-platforms → L1 (unit/integration изменённых модулей) → L2 (smoke-сценарии через MCP/adb) → aggregate → verdict`
Переходы: L1↔L2 независимы (можно параллельно); при падении → `Chaining: pr-check → bug-fix` (или `incident` для прод).
`identify-platforms` — если diff трогает `commonMain`, smoke прогнать на **обеих** платформах (parity). Persistent: `./swarm-report/<slug>-pr-check.md` + скрины smoke в `smoke/shots/`.

## Сабагенты по стадиям
| Стадия | Роль → сабагент | Модель | Цель |
|---|---|---|---|
| gather-diff | @Reviewer `alva-review-expert` / session | sonnet | что изменил PR, какие модули/экраны/платформы затронуты |
| L1 tests | @QA `general-purpose` | sonnet | запустить unit/integration тесты (kotlin.test/Turbine) затронутых модулей, зелёные |
| L2 smoke | @DevOps/session (adb) или claude-in-mobile MCP | sonnet | протыкать сценарии, скрин на каждом шаге, PASS/FAIL (Android; iOS при shared) |
| aggregate | @Reviewer `alva-review-expert` | sonnet | единый отчёт L1+L2 |

## MCP / Skills (обязательные)
`claude-in-mobile` (мобилка) или **adb** по эмулятору · ast-index · Sentry ·
профиль `test` (L1 тест-конвенции: kotlin.test + Turbine) · `smoke/scenarios.md` проекта · **DeepWiki**.

## MUST (обязан)
- Прогнать **оба** уровня. L1 — реально запустить тест-таск (не «на глаз»). L2 — реальные тапы + **скрин на каждом шаге**.
- **Diff в `commonMain` → smoke на обеих платформах** (platform parity).
- Единый отчёт: L1 (N tests passed/failed) + L2 (сценарии PASS/FAIL + скрины) + итоговый вердикт.
- При падении — указать **где** проблема (файл/строка для L1; шаг/экран + logcat FATAL для L2).

## MUST NOT (нельзя)
- Мержить/деплоить на красном (L1 fail или L2 FAIL).
- Пропускать smoke «потому что тесты зелёные» (и наоборот).
- Заявлять «прошло» без реального прогона.

## Формат ответа
```
## PR-Check отчёт (alva)
Платформы: Android / iOS / shared
L1 (код): N тестов, N passed, N failed [файл:строка если fail]
L2 (smoke): S1..S5 — PASS/FAIL, скрины shots/*.png [шаг+диагноз если fail]
Вердикт: MERGE-READY / BLOCKED (причина)
```

## Chaining / вариация «задеплоил фичу»
- Запрос «я задеплоил новую фичу — обнови smoke и прогони всё заново»: сперва **обновить `smoke/scenarios.md`**
  (добавить шаги под новую фичу — новые экраны/действия), затем полный прогон L1+L2 и единый отчёт.
- Любой FAIL → `Chaining: pr-check → bug-fix` (прод → `incident`), передать диагноз/скрин/стек.
