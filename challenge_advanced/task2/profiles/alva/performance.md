# Профиль: performance — alva (KMM+CMP baby-care)

> Контекст **alva** (Kotlin Multiplatform + Compose Multiplatform, baby-care). Роли → сабагенты из `alva/roster.md`;
> общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md` (не дублировать).
> Стек: KMP · CMP (shared обе платформы) · Koin · Compose Navigation 3 · UDF со **Event** · `Alva`-префикс DS ·
> доки — **DeepWiki**. Build: `./gradlew :androidApp:assembleDebug` (+ Xcode iOS).

## Назначение / когда активен
Оптимизация метрик с доказательством **числами**: recomposition (CMP), холодный старт, build-time, размер артефакта,
память/утечки, jank.
**Триггеры:** «тормозит», «лагает», «долгий старт», «recomposition», «размер приложения», «медленная сборка», «утечка памяти».
**Примеры:** лишний recomposition из-за unstable-параметра в shared Composable (XS); горячий путь экрана дневника (M); старт/память (L).

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | одна очевидная просадка (unstable-параметр, лишний recomposition) | session-only: `alva-android-ui-expert`/`alva-kotlin-expert` + профилировщик |
| S | локальная оптимизация с замером | `alva-kotlin-expert` → замер |
| M | горячий путь / один экран | консилиум-hypothesize → `alva-kotlin-expert`/`alva-android-ui-expert` → замер |
| L | системная (старт, память, размер) на обеих платформах | `alva-planner-expert` + консилиум → `alva-kotlin-expert`(+`alva-android-ui-expert`) → замер |
| XL | сквозная перф-кампания | full team + рекурсивные SubLead |

## Стадии (DAG)
`measure → identify-platforms → hypothesize → optimize → measure → report → done`.
`measure(ДО)` — baseline числами (профиль/трейс/метрика, на какой платформе). `identify-platforms` — где просадка: Android, iOS или shared. `hypothesize` — гипотезы, что и почему медленно.
`optimize` — точечная правка топ-гипотезы. `measure(ПОСЛЕ)` — те же метрики, доказать дельту. Нет улучшения →
откат + назад в `hypothesize`. Persistent: `./swarm-report/<slug>-perf.md` (baseline-числа, платформа, гипотезы, дельты) —
перечитывать, отмечать `[x]`.

## Сабагенты по стадиям
| Стадия | Роль → сабагент | Модель | Цель |
|---|---|---|---|
| measure (ДО) | @DevOps (Bash) + @QA `general-purpose` | Sonnet | снять baseline: профиль/трейс/метрика (платформа), зафиксировать числа |
| hypothesize | консилиум: @Architect `alva-planner-expert` · @UIDev `alva-android-ui-expert` (recomposition) · @BackendDev `alva-kotlin-expert` (I/O) · @DevOps (build/размер) | Opus | параллельно гипотезы по доменам, ранжир по impact |
| optimize | @Dev `alva-kotlin-expert` · @UIDev `alva-android-ui-expert` | Sonnet | точечная правка топ-гипотезы, поведение сохранить |
| measure (ПОСЛЕ) | @DevOps (Bash) + @QA `general-purpose` | Sonnet | те же замеры, дельта ДО/ПОСЛЕ числами; поведение не регрессировало |
| report | оркестратор | — | baseline / гипотезы / правка / дельта числами |

## MCP / Skills (обязательные)
`jetpack-compose-audit` (recomposition/state/side-effects — применимо к CMP) · `ast-index`
· **DeepWiki** (перф-паттерны KMP/Compose) · claude-in-mobile (jank/старт вживую) · caveman. Skills: `alva-project-context` ·
`compose-principles` · `alva-viewmodel`.

## MUST (обязан)
- Замер ДО и ПОСЛЕ — **числами** (мс, кол-во recomposition, МБ, сек сборки); без числа улучшение не заявлять.
- **Определить платформу просадки** (Android/iOS/shared); при shared-правке — проверить, что не регрессировало на обеих (parity).
- Профилировать перед правкой — найти реальное узкое место, не догадку.
- Поведение сохранить (перф — не изменение функциональности); regression-check в `measure(ПОСЛЕ)`.

## MUST NOT (нельзя)
- Оптимизировать без замера (вслепую).
- Преждевременная оптимизация — микро-правки без доказанного узкого места / вне горячего пути.
- Заявлять улучшение без дельты ДО/ПОСЛЕ.
- Жертвовать корректностью / читаемостью / platform parity ради мнимой перф-выгоды.

## Формат ответа
Baseline (метрика = число, платформа) · гипотезы (ранжир по impact) · правка (файлы — абсолютные пути) · результат
(ДО→ПОСЛЕ дельта числами) · вывод (стоило / нет). Код — только если load-bearing.

**Маркировка прогресса — обязательна на каждом шаге task execution:**
- **Старт шага:** `▶️ **ШАГ <n>/<N> · <стадия>** — <название шага>`
- **Задача шага:** `🎯 **Задача:** <что именно делаем — одна строка>`
- **Итог шага:** `✅ **Итог:** <главная мысль>` · провал — `❌ **Провал:** <что сломалось + где>` · частично — `⚠️ **Частично:** <что осталось>`
- **Переход стадии:** `🔀 **Переход:** <стадия> → <стадия>` · чейнинг — `⛓️ **Chaining:** <profile> → <profile>`

Каждая метка — отдельной строкой, иконка + **жирный** лейбл, не сливать с прозой. Между шагами — `---`.
Без маркировки шаг считается незакрытым.

## Chaining (если апстрим)
Обычно standalone. Может принимать вход от `incident → performance` (перф-инцидент) — тогда `measure(ДО)`
стартует с прод-сигнала. Сам не апстрим: терминал `done`.
