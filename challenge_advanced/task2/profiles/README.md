# Profiles — агентные режимы работы

Профиль = **режим работы ассистента** под тип задачи. Он задаёт весь флоу: стадии (DAG), какие
сабагенты/команды на каждой стадии, какие MCP/skills, что МОЖНО/НЕЛЬЗЯ, формат ответа. Выбранный
профиль определяет, «в каком стиле» ассистент ведёт всю разработку.

## Структура (DRY)
```
profiles/
  README.md            ← этот файл
  _TEMPLATE.md         ← шаблон профиля
  _shared/
    orchestration.md   ← стадии-DAG, консилиум, persistent-файлы, chaining, шкала XS→XL
    conventions.md     ← общие конвенции + дельты стеков + указатели на скиллы (single source)
    profiles/          ← 15 УНИВЕРСАЛЬНЫХ flow (стек-агностик): feature, bug-fix, refactor, migration,
                          performance, research, review, test, security-audit, architecture,
                          design, requirements, release, incident, docs
  base/  roster.md      ← контекст: кросс-платформа (Android + KMM + Backend), generic-сабагенты
  xbet/  roster.md      ← контекст: Mobile_Android_OnexBet (Android, Dagger/Cicerone, xbet-* агенты)
  alva/  roster.md      ← контекст: Alva (KMM+CMP, Koin/Nav3, alva-* агенты)
```
Профиль = `_shared/profiles/<name>.md` (flow) ⨯ `<context>/roster.md` (стек + сабагенты). Одни и те же
15 профилей работают в любом контексте — стек-специфика приходит из roster на этапе создания задачи.

## Выбор профиля
- **Явно:** `профиль: <name> · контекст: <base|xbet|alva> · размер: <XS|S|M|L|XL>`.
- **Авто:** по ключевым словам запроса (баг/краш → bug-fix; «как устроено…» → research; «мигрируй» →
  migration; «отревьюь» → review; «релиз» → release; дизайн/Figma → design; …). Контекст — по CWD/проекту.
- При неоднозначности — уточнить ОДИН раз (профиль/размер/контекст) и зафиксировать в plan-файле.

## Chaining (профили вызывают друг друга)
Часть профилей — «апстрим»: делают свою часть и **запускают** исполнительный профиль:
- **design** → по готовности макета запускает **feature**.
- **requirements** → запускает **architecture** или **feature**.
- **architecture** → запускает **feature** / **refactor** / **migration**.
- **incident** → воспроизвёл прод-краш → запускает **bug-fix** (urgent-вариант).

## Размер задачи (XS→XL)
Каждый профиль масштабируется по шкале из `team-lead-orchestration`: XS — session-only (1-2 сабагента),
… XL — полная команда + рекурсивные SubLead (глубина 2). См. `_shared/orchestration.md`.
