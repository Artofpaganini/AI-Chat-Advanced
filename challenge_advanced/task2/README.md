# Task 2 — Профили (персонализация флоу под тип задачи)

Оптимизация глобального CLAUDE.md: добавлена система **профилей** — режимов работы ассистента под тип
задачи. Выбранный профиль задаёт весь флоу разработки (стадии · сабагенты · MCP/skills · формат ответа).

## Что здесь (снапшот логики)
```
global/CLAUDE.md         — оттюнингованный глобальный ~/.claude/CLAUDE.md (+ секция «Профили»)
profiles/                — система профилей (см. profiles/README.md)
  _shared/orchestration.md · conventions.md
  _shared/profiles/       — 15 УНИВЕРСАЛЬНЫХ flow (стек-агностик)
  base/ · xbet/ · alva/   — roster'ы (стек + сабагенты по контексту)
agents/                  — 19 сабагентов (10 alva + 9 xbet) — снапшот
skills/                  — проектные + shared скиллы — снапшот
```

## 15 профилей (универсальные, size-aware XS→XL, одинаковые в base/xbet/alva)
**Изменение кода:** feature · bug-fix · refactor · migration · performance
**Понять/проверить:** research · review · test · security-audit
**Спроектировать:** requirements · design · architecture
**Отгрузить/эксплуатация:** release · incident
**Документация:** docs

Профиль = `_shared/profiles/<name>.md` (flow) ⨯ `<context>/roster.md` (стек+сабагенты). Стек-специфика
(Dagger→Koin, Cicerone vs Nav3, SideEffect vs Event) резолвится из roster на создании задачи — не в профиле.

## Chaining (профили вызывают друг друга)
`design → feature` · `requirements → architecture|feature` · `architecture → feature|refactor|migration`
· `incident → bug-fix`. Апстрим делает свою часть и передаёт артефакт исполнительному профилю.

## Реорганизация (на ПК, не в этом репо)
Проектные profiles/subagents/skills теперь лежат в `<project>/.claude/` (git-excluded), симлинки в
`~/.claude/`. Единый паттерн для xbet и alva. Кросс-проектное (base, _shared, shared-skills, глобал) —
в `~/.claude/`.

> Это снапшот-копия для челленджа. Живые файлы — в `~/.claude/` и `<project>/.claude/`.
