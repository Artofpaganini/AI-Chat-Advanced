# Профиль: refactor — alva (KMM+CMP baby-care)

> Контекст **alva** (Kotlin Multiplatform + Compose Multiplatform, baby-care). Роли → сабагенты из `alva/roster.md`;
> общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md` (не дублировать).
> Стек: KMP · CMP (shared обе платформы) · Koin · Compose Navigation 3 · UDF со **Event** · `Alva`-префикс DS ·
> Kotlin DSL + version catalog · доки — **DeepWiki**. Build: `./gradlew :androidApp:assembleDebug` (+ Xcode iOS).

## Назначение / когда активен
Изменение структуры кода **без изменения поведения** (извлечение, переименование, расслоение, дедуп).
**Триггеры:** «отрефактори», «вынеси», «упрости», «переименуй», «расслои», «убери дублирование».
**Примеры:** rename символа (XS); извлечь use-case/маппер (S); расслоить модуль или вынести общее в `commonMain` (M); ре-дизайн границ пакетов (XL).

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | переименование символа, extract-переменной | session-only: `Explore` + 1 исполнитель |
| S | извлечь use-case/маппер, разнести файл | `alva-kotlin-expert` → `alva-review-expert` |
| M | расслоение модуля, дедуп по нескольким файлам, вынос в commonMain | `alva-planner-expert` (план) → `alva-kotlin-expert` → `alva-review-expert` |
| L | реструктуризация фичи/пакета | `alva-planner-expert` → `alva-kotlin-expert`(+`alva-android-ui-expert`) → `alva-review-expert`, SubLead по надобности |
| XL | кросс-модульный ре-дизайн границ | full team + рекурсивные SubLead |

## Стадии (DAG)
`baseline → plan → execute → validation → report → done`.
`baseline` — зелёный build + прогон существующих тестов **ДО** (эталон, зафиксировать вывод). Переходы
линейно; `validation` сравнивает с baseline, при расхождении → назад в `execute`. **Правка shared-кода → build/тесты на обеих платформах** (parity). Persistent:
`./swarm-report/<slug>-refactor.md` (baseline-результаты, шаги, чек-лист поведения) — перечитывать, отмечать `[x]`.

## Сабагенты по стадиям
| Стадия | Роль → сабагент | Модель | Цель |
|---|---|---|---|
| baseline | @DevOps (Bash) | — | зелёный build (`:androidApp:assembleDebug` + iOS при shared) + прогон тестов ДО; сохранить вывод как эталон |
| plan | @Architect `alva-planner-expert` | Opus | разбить на мелкие behavior-preserving шаги, порядок, точки проверки |
| execute | @Dev `alva-kotlin-expert` · @UIDev `alva-android-ui-expert` | Sonnet | мелкими шагами, каждый компилируется; `simplify` для quality-cleanup |
| validation | @Reviewer `alva-review-expert` + @DevOps (Bash) | Opus/Sonnet | build зелёный ПОСЛЕ + те же тесты дают тот же результат = поведение сохранено |
| report | оркестратор | — | baseline / изменения / доказательство сохранения поведения |

## MCP / Skills (обязательные)
`ast-index` (usages/callers перед extract/rename — обязательно) · `simplify` (reuse/эффективность/altitude)
· **DeepWiki** · caveman. Skills: `alva-project-context` · `alva-udf-architecture` ·
`alva-viewmodel` · `compose-principles`. Тесты — **существующие** (новые — opt-in).

## MUST (обязан)
- Доказать неизменность поведения: build + тесты ДО (baseline) и ПОСЛЕ дают идентичный результат.
- **Правка `commonMain` → проверить обе платформы** (build `:androidApp:assembleDebug` + iOS/Xcode, parity сохранён).
- Мелкие проверяемые шаги (каждый компилируется); ast-index — все usages перед extract/rename.
- Сохранять публичные контракты/сигнатуры (и `expect/actual`), если задача не про их изменение.

## MUST NOT (нельзя)
- Менять поведение (фичи, баг-фиксы, изменение вывода) под видом рефактора.
- Подмешивать новую функциональность / фичи «заодно».
- Рефакторить без baseline (нечего сравнивать).
- Ломать platform parity / `expect-actual`-контракты; ослаблять / удалять тесты, чтобы «сошлось».

## Формат ответа
Baseline (что было зелёным) · структурные изменения (файлы — абсолютные пути) · доказательство сохранения
поведения (build + тесты ДО = ПОСЛЕ, платформы) · что НЕ менялось (контракты). Код — только если load-bearing.

## Chaining (если апстрим)
**Downstream от `architecture → refactor`.** На входе — целевая структура/границы из архитектурного артефакта.
Сам не апстрим: терминал `done`.
