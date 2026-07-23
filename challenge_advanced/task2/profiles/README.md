# Profiles - агентные режимы работы

Профиль = **режим работы ассистента** под тип задачи. Задаёт весь флоу: стадии (DAG), сабагенты по стадиям,
MCP/skills, что МОЖНО/НЕЛЬЗЯ, формат ответа. Выбранный профиль определяет, «в каком стиле» ведётся разработка.

## Структура (самодостаточные каталоги)
```
profiles/
  README.md · _TEMPLATE.md          ← этот файл + шаблон нового профиля
  base/                             ← кросс-платформа (Android + KMM + Backend), generic-сабагенты
    <16 профилей>.md · roster.md · conventions.md
  xbet/                             ← Mobile_Android_OnexBet (+twin xbet1): Dagger/Cicerone/SideEffect, xbet-*
    <16 профилей>.md · roster.md · conventions.md
  alva/                             ← Alva (KMM+CMP): Koin/Nav3/Event, alva-*, iOS/platform-parity
    <16 профилей>.md · roster.md · conventions.md
```
Каждый каталог **самодостаточен**: 16 затюненных профилей + `roster.md` (стек+сабагенты) + `conventions.md`
(примеры кода хорошо/плохо/шаблон под свой стек). Общее (оркестрация, размерность XS->XL, консилиум, chaining,
общие конвенции, стек-2026, выбор профиля) - в глобальном `~/.claude/CLAUDE.md`, всегда загружен.

## 16 профилей (одинаковый набор в каждом каталоге, затюнены под контекст)
feature · bug-fix · refactor · migration · performance · research · review · test · security-audit ·
architecture · design · requirements · release · incident · docs · pr-check

## Выбор профиля
- **Явно:** `профиль: <name> · контекст: <base|xbet|alva> · размер: <XS|S|M|L|XL>`.
- **Авто:** по ключевым словам запроса; контекст - по CWD/проекту. Неоднозначно -> уточнить ОДИН раз.

## Chaining (профили вызывают друг друга)
`design -> feature` · `requirements -> architecture|feature` · `architecture -> feature|refactor|migration`
· `incident -> bug-fix`. Апстрим делает свою часть и передаёт артефакт исполнительному профилю.

## Размерность (XS->XL)
Каждый профиль масштабируется: XS - session-only (1-2 сабагента) … XL - полная команда + рекурсивные SubLead.
Детали - секции «Оркестрация»/«Стадии задачи»/«Профили» глобального `~/.claude/CLAUDE.md`.
