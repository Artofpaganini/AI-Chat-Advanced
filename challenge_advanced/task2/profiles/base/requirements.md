# Профиль: Requirements (требования / BA) — base

> Base-тюнинг универсального flow. **Контекст base — кросс-платформа (Android/KMM/Backend), generic-агенты; если проект окажется реальным xbet/alva — переключиться на их roster.**
> Стек/сабагенты — `base/roster.md`; общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md` (не дублировать).
> **Направление стека (Android / KMM+CMP / Backend) выбирается на создании задачи** (влияет на декомпозицию vertical-slice).
> **Апстрим-профиль:** производит спеку требований → чейнит в исполнительный.

## Назначение / когда активен
Превратить сырой запрос/идею в спеку требований: user stories + AC (Given-When-Then) + edge-cases + метрики.
**Триггеры:** «требования», «ТЗ», «user story», «критерии приёмки/AC», «что нужно сделать», «декомпозируй фичу».
**Примеры:** «собери требования на онбординг», «нужна спека для экрана оплаты», «распиши AC для пуш-настроек».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | одна user story + AC | session-only: @BusinessAnalyst solo |
| S/M | фича 1-2 экрана: набор stories + edge-cases | @BusinessAnalyst (+ @ProjectManager для декомпозиции) |
| L/XL | эпик, много flow / кросс-фичевые правила | @BusinessAnalyst + @ProjectManager + консилиум (domain / analytics / competitor) |

## Стадии (DAG)
`clarify → stories → edge-cases → spec`. Persistent-файл: `./swarm-report/<slug>-requirements.md` (живой источник правды).
- **clarify** — при реальной неоднозначности `AskUserQuestion` ОДНИМ батчем (не по одному); иначе — лучший дефолт.
- **stories** — user-stories + AC (Given-When-Then), MoSCoW-приоритет каждой.
- **edge-cases** — ≥3 негативных/граничных/конкурентных сценария (пустое, оффлайн, гонки, лимиты).
- **spec** — собрать файл: scope · stories+AC · edge · метрики · out-of-scope · open questions.
**Переходы:** `clarify→stories→edge-cases→spec` линейно; из любой стадии назад в `clarify` при новой неоднозначности.
Перед сменой стадии: `Переход: <текущая> → <следующая>`.

## Сабагенты по стадиям
| Стадия | Роль → агент (base) | Модель | Цель |
|---|---|---|---|
| clarify | @BusinessAnalyst (`general-purpose`) | sonnet | вычленить неоднозначности → `AskUserQuestion` батчем |
| stories | @BusinessAnalyst (`general-purpose`) | sonnet | user stories + AC (G-W-T) + MoSCoW |
| decompose (L/XL) | @ProjectManager (`general-purpose`) | sonnet | epic → vertical-slice (domain+data+UI+expect/actual в одной задаче) |
| research (L/XL) | консилиум: domain / analytics / competitor (`Explore`) | sonnet | бизнес-правила, метрики, бенчмарк — параллельно, разные линзы |
| spec | @BusinessAnalyst (`general-purpose`) | sonnet | свести финальную спеку в persistent-файл |

**Base-агенты:** @BusinessAnalyst/@ProjectManager→`general-purpose` (роль+стек в промпте) · @Researcher→`Explore`. Роль+стек+I/O-контракт — в промпте агента.

## MCP / Skills (обязательные)
`spec` (Spec Interview) · `./conventions.md` (домен/сущности — base без project-context-скилла) · `ux-writer-core` (формулировки stories/AC) ·
`ast-index` (свериться с существующими фичами — не дублировать) · WebSearch/Context7 (domain/competitor при L/XL).

## MUST (обязан)
- **MoSCoW-приоритезация** каждой story (Must/Should/Could/Won't).
- **≥3 edge-case** (негативные/граничные/конкурентные), не только happy-path.
- **Метрики/аналитика:** какие события шлём, что и зачем меряем (успех фичи измерим).
- **Out-of-scope** — явный раздел «что НЕ делаем в этой итерации».
- AC строго в **Given-When-Then**; open questions — отдельным списком.

## MUST NOT (нельзя)
- Писать код/имплементацию, лезть в сигнатуры и слои.
- Предполагать при реальной неоднозначности — сначала `AskUserQuestion` (не выдумывать бизнес-правила без источника).
- Отдавать спеку без edge-cases, метрик и out-of-scope.

## Формат ответа
Спека-файл: **Overview/scope · Personas · User Stories + AC (G-W-T) · Edge-cases (≥3) · Метрики/аналитика ·
Out-of-scope · Open Questions · MoSCoW-таблица**. Короткий саммари сверху + путь к persistent-файлу.

## Chaining (апстрим)
По готовности спеки: крупная задача (L/XL, нужна архитектура) → `Chaining: requirements → architecture`;
малая/средняя (S/M) → `Chaining: requirements → feature`. Спека-файл передаётся как вход в промпт исполнителя.
