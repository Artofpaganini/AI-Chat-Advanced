# Профиль: refactor — xbet

> Контекст **xbet** (`Mobile_Android_OnexBet`); также обслуживает twin **xbet1** (`own_xbet`).
> Android-only · Kotlin · Compose · **Dagger 2** (+Koin-track) · **Cicerone `XPlatformRouter`** (не менять) ·
> UDF со **SideEffect** · Build `./gradlew assembleBetaDebug`.
> Стек/сабагенты — `roster.md`. Общее — `../_shared/orchestration.md` и `../_shared/conventions.md` (не дублировать).

## Назначение / когда активен
Изменение структуры кода **без изменения поведения** (извлечение, переименование, расслоение, дедуп).
**Триггеры:** «отрефактори», «вынеси», «упрости», «переименуй», «расслои», «убери дублирование».
**Примеры:** rename символа (XS); извлечь use-case/маппер (S); расслоить модуль (M); ре-дизайн границ пакетов (XL).

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | переименование символа, extract-переменной | session-only: `Explore` + 1 исполнитель |
| S | извлечь use-case/маппер, разнести файл | `xbet-kotlin-expert` → `xbet-review-expert` |
| M | расслоение модуля, дедуп по нескольким файлам | `xbet-planner-expert` (план) → `xbet-kotlin-expert` → `xbet-review-expert` |
| L | реструктуризация фичи/пакета | `xbet-planner-expert` → `xbet-kotlin-expert`(+`xbet-compose-expert`) → `xbet-review-expert`, SubLead по надобности |
| XL | кросс-модульный ре-дизайн границ | full team + рекурсивные SubLead |

## Стадии (DAG)
`baseline → plan → execute → validation → report → done`.
`baseline` — зелёный `./gradlew assembleBetaDebug` + прогон существующих тестов **ДО** (эталон, зафиксировать
вывод). Переходы линейно; `validation` сравнивает с baseline, при расхождении → назад в `execute`. Persistent:
`./swarm-report/<slug>-refactor.md` (baseline-результаты, шаги, чек-лист поведения) — перечитывать, отмечать `[x]`.

## Сабагенты по стадиям
| Стадия | Роль (subagent) | Модель | Цель |
|---|---|---|---|
| baseline | Bash (@DevOps) | — | зелёный `assembleBetaDebug` + прогон тестов ДО; сохранить вывод как эталон |
| plan | `xbet-planner-expert` | Opus | разбить на мелкие behavior-preserving шаги, порядок, точки проверки |
| execute | `xbet-kotlin-expert` · `xbet-compose-expert` | Sonnet | мелкими шагами, каждый компилируется; `simplify` для quality-cleanup |
| validation | `xbet-review-expert` + Bash (@DevOps) | Opus/Sonnet | build зелёный ПОСЛЕ + те же тесты дают тот же результат = поведение сохранено |
| report | оркестратор | — | baseline / изменения / доказательство сохранения поведения |

## MCP / Skills (обязательные)
`ast-index` (usages/callers перед extract/rename — обязательно) · `simplify` (reuse/эффективность/altitude)
· **Context7** · caveman. Skills: `xbet-project-context` · `xbet-udf-architecture` · `xbet-viewmodel` ·
`xbet-reference-modules` · `compose-principles`. Тесты — **существующие** (новые — opt-in).

## MUST (обязан)
- Доказать неизменность поведения: build + тесты ДО (baseline) и ПОСЛЕ дают идентичный результат.
- Мелкие проверяемые шаги (каждый компилируется); ast-index — все usages перед extract/rename.
- Сохранять публичные контракты/сигнатуры, если задача не про их изменение (visibility — `internal`-по-умолчанию).

## MUST NOT (нельзя)
- Менять поведение (фичи, баг-фиксы, изменение вывода) под видом рефактора.
- Подмешивать новую функциональность / фичи «заодно».
- Трогать классы Cicerone / `XPlatformRouter`.
- Рефакторить без baseline (нечего сравнивать).
- Ослаблять / удалять тесты, чтобы «сошлось».

## Формат ответа
Baseline (что было зелёным) · структурные изменения (файлы — абсолютные пути) · доказательство сохранения
поведения (build + тесты ДО = ПОСЛЕ) · что НЕ менялось (контракты). Код — только если load-bearing.

## Chaining (если апстрим)
**Downstream от `architecture → refactor`.** На входе — целевая структура/границы из архитектурного артефакта.
Сам не апстрим: терминал `done`.
