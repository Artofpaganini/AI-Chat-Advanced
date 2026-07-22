# Профиль: performance — xbet

> Контекст **xbet** (`Mobile_Android_OnexBet`); также обслуживает twin **xbet1** (`own_xbet`).
> Android-only · Compose/Material3 · **Dagger 2** · UDF со **SideEffect** · Build `./gradlew assembleBetaDebug` · R8.
> Стек/сабагенты — `roster.md`. Общее — `../_shared/orchestration.md` и `../_shared/conventions.md` (не дублировать).

## Назначение / когда активен
Оптимизация метрик с доказательством **числами**: recomposition, холодный старт, build-time, R8/размер APK,
память/утечки, jank.
**Триггеры:** «тормозит», «лагает», «долгий старт», «recomposition», «размер APK», «медленная сборка», «утечка памяти».
**Примеры:** лишний recomposition из-за unstable-параметра (XS); горячий путь экрана (M); старт/память/размер (L).

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | одна очевидная просадка (unstable-параметр, лишний recomposition) | session-only: `xbet-compose-expert`/`xbet-kotlin-expert` + профилировщик |
| S | локальная оптимизация с замером | `xbet-kotlin-expert` → замер |
| M | горячий путь / один экран | консилиум-hypothesize → `xbet-compose-expert`/`xbet-kotlin-expert` → замер |
| L | системная (старт, память, размер APK) | `xbet-planner-expert` + консилиум → `xbet-kotlin-expert`(+`xbet-compose-expert`) → замер |
| XL | сквозная перф-кампания | full team + рекурсивные SubLead |

## Стадии (DAG)
`measure → hypothesize → optimize → measure → report → done`.
`measure(ДО)` — baseline числами (профиль/трейс/метрика). `hypothesize` — гипотезы, что и почему медленно.
`optimize` — точечная правка топ-гипотезы. `measure(ПОСЛЕ)` — те же метрики, доказать дельту. Нет улучшения →
откат + назад в `hypothesize`. Persistent: `./swarm-report/<slug>-perf.md` (baseline-числа, гипотезы, дельты) —
перечитывать, отмечать `[x]`.

## Сабагенты по стадиям
| Стадия | Роль (subagent) | Модель | Цель |
|---|---|---|---|
| measure (ДО) | Bash (@DevOps) + `xbet-tester-expert` | Sonnet | снять baseline: профиль/трейс/метрика, зафиксировать числа |
| hypothesize | консилиум: `xbet-planner-expert` · `xbet-compose-expert` (recomposition) · `xbet-kotlin-expert` (I/O) · Bash (build/R8) | Opus | параллельно гипотезы по доменам, ранжир по impact |
| optimize | `xbet-kotlin-expert` · `xbet-compose-expert` | Sonnet | точечная правка топ-гипотезы, поведение сохранить |
| measure (ПОСЛЕ) | Bash (@DevOps) + `xbet-tester-expert` | Sonnet | те же замеры, дельта ДО/ПОСЛЕ числами; поведение не регрессировало |
| report | оркестратор | — | baseline / гипотезы / правка / дельта числами |

## MCP / Skills (обязательные)
`jetpack-compose-audit` (recomposition/state/side-effects) · `r8-analyzer` (keep-rules/размер) · `ast-index`
· **Context7** · claude-in-mobile (jank/старт вживую) · caveman. Skills: `xbet-project-context` ·
`compose-principles` · `xbet-viewmodel`.

## MUST (обязан)
- Замер ДО и ПОСЛЕ — **числами** (мс, кол-во recomposition, МБ, сек сборки); без числа улучшение не заявлять.
- Профилировать перед правкой — найти реальное узкое место, не догадку.
- Поведение сохранить (перф — не изменение функциональности); regression-check в `measure(ПОСЛЕ)`.

## MUST NOT (нельзя)
- Оптимизировать без замера (вслепую).
- Преждевременная оптимизация — микро-правки без доказанного узкого места / вне горячего пути.
- Заявлять улучшение без дельты ДО/ПОСЛЕ.
- Жертвовать корректностью / читаемостью ради мнимой перф-выгоды.

## Формат ответа
Baseline (метрика = число) · гипотезы (ранжир по impact) · правка (файлы — абсолютные пути) · результат
(ДО→ПОСЛЕ дельта числами) · вывод (стоило / нет). Код — только если load-bearing.

## Chaining (если апстрим)
Обычно standalone. Может принимать вход от `incident → performance` (перф-инцидент) — тогда `measure(ДО)`
стартует с прод-сигнала. Сам не апстрим: терминал `done`.
