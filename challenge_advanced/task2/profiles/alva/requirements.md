# Профиль: Requirements — alva (KMM+CMP baby-care)

> Контекст **alva** (Kotlin Multiplatform + Compose Multiplatform, baby-care). Роли → сабагенты из `alva/roster.md`;
> общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md` (не дублировать).
> Стек: KMP · CMP (shared обе платформы) · Koin · Compose Navigation 3 · UDF со **Event** · `Alva`-префикс DS ·
> `composeResources/` · доки — **DeepWiki**. Build: `./gradlew :androidApp:assembleDebug` (+ Xcode iOS).
> **Апстрим-профиль:** производит спеку требований → чейнит в исполнительный.

## Назначение / когда активен
Превратить сырой запрос/идею в спеку требований: user stories + AC (Given-When-Then) + edge-cases + метрики + **платформенный охват**.
**Триггеры:** «требования», «ТЗ», «user story», «критерии приёмки/AC», «что нужно сделать», «декомпозируй фичу».
**Примеры:** «собери требования на трекинг сна», «нужна спека для экрана добавления кормления», «распиши AC для пуш-напоминаний».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | одна user story + AC | session-only: `alva-ba-expert` solo |
| S/M | фича 1-2 экрана: набор stories + edge-cases | `alva-ba-expert` (+ `alva-project-manager-expert` для декомпозиции) |
| L/XL | эпик, много flow / кросс-фичевые правила | `alva-ba-expert` + `alva-project-manager-expert` + консилиум (domain / analytics / competitor) |

## Стадии (DAG)
`clarify → identify-platforms → stories → edge-cases → spec`. Persistent-файл: `./swarm-report/<slug>-requirements.md` (живой источник правды).
- **clarify** — при реальной неоднозначности `AskUserQuestion` ОДНИМ батчем (не по одному); иначе — лучший дефолт.
- **identify-platforms** — фича на Android, iOS или обеих (дефолт — обе, shared); отметить платформо-специфичные требования (пуши, биометрия, файлы) и **parity**.
- **stories** — user-stories + AC (Given-When-Then), MoSCoW-приоритет каждой.
- **edge-cases** — ≥3 негативных/граничных/конкурентных сценария (пустое, оффлайн, гонки, лимиты).
- **spec** — собрать файл: scope · платформы · stories+AC · edge · метрики · out-of-scope · open questions.
**Переходы:** линейно; из любой стадии назад в `clarify` при новой неоднозначности.
Перед сменой стадии: `Переход: <текущая> → <следующая>`.

## Сабагенты по стадиям
| Стадия | Роль → сабагент | Модель | Цель |
|---|---|---|---|
| clarify | @BusinessAnalyst `alva-ba-expert` | sonnet | вычленить неоднозначности → `AskUserQuestion` батчем |
| stories | @BusinessAnalyst `alva-ba-expert` | sonnet | user stories + AC (G-W-T) + MoSCoW |
| decompose (L/XL) | @ProjectManager `alva-project-manager-expert` | sonnet | epic → vertical-slice (domain+data+UI+expect/actual в одной задаче) |
| research (L/XL) | консилиум: domain / analytics / competitor | sonnet | бизнес-правила baby-care, метрики, бенчмарк — параллельно, разные линзы |
| spec | @BusinessAnalyst `alva-ba-expert` | sonnet | свести финальную спеку в persistent-файл |

## MCP / Skills (обязательные)
`spec` (Spec Interview) · `alva-project-context` (домен baby-care/сущности) · `ux-writer-core` (формулировки stories/AC) ·
`ast-index` (свериться с существующими фичами — не дублировать) · WebSearch/**DeepWiki** (domain/competitor при L/XL).

## MUST (обязан)
- **Платформенный охват:** явно указать Android/iOS/обе + platform parity; платформо-специфичные требования отметить.
- **MoSCoW-приоритезация** каждой story (Must/Should/Could/Won't).
- **≥3 edge-case** (негативные/граничные/конкурентные), не только happy-path.
- **Метрики/аналитика:** какие события шлём, что и зачем меряем (успех фичи измерим).
- **Out-of-scope** — явный раздел «что НЕ делаем в этой итерации».
- AC строго в **Given-When-Then**; open questions — отдельным списком.

## MUST NOT (нельзя)
- Писать код/имплементацию, лезть в сигнатуры и слои.
- Предполагать при реальной неоднозначности — сначала `AskUserQuestion` (не выдумывать бизнес-правила без источника).
- Отдавать спеку без edge-cases, метрик, платформенного охвата и out-of-scope.

## Формат ответа
Спека-файл: **Overview/scope · Платформы (parity) · Personas · User Stories + AC (G-W-T) · Edge-cases (≥3) · Метрики/аналитика ·
Out-of-scope · Open Questions · MoSCoW-таблица**. Короткий саммари сверху + путь к persistent-файлу.

## Chaining (апстрим)
По готовности спеки: крупная задача (L/XL, нужна архитектура) → `Chaining: requirements → architecture`;
малая/средняя (S/M) → `Chaining: requirements → feature`. Спека-файл передаётся как вход в промпт исполнителя.
