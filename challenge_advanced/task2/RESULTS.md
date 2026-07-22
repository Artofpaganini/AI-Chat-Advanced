# Task 2 — результат

## Что сделано
1. **Система профилей** — 15 универсальных агентных режимов (стек-агностик, size-aware XS→XL, одинаковые
   в base/xbet/alva; стек резолвится из roster на создании задачи):
   - Изменение кода: `feature` · `bug-fix` · `refactor` · `migration` · `performance`
   - Понять/проверить: `research` · `review` · `test` · `security-audit`
   - Спроектировать: `requirements` · `design` · `architecture`
   - Отгрузить/эксплуатация: `release` · `incident`
   - Документация: `docs`
   - **Chaining**: `design→feature`, `requirements→architecture|feature`, `architecture→feature|refactor|migration`, `incident→bug-fix`.
2. **Фундамент** — `_shared/orchestration.md` (стадии-DAG, консилиум, persistent-файлы, размерность),
   `_shared/conventions.md` (single-source конвенций + дельты стеков), 3× `roster.md`, `README`, `_TEMPLATE`.
3. **Реорганизация тулинга** — проектные profiles/subagents/skills лежат в `<project>/.claude/`
   (git-excluded), симлинки в `~/.claude/`. Единый паттерн: xbet, xbet1 (own_xbet), alva.
4. **Глобальный CLAUDE.md** — добавлена секция «Профили» (выбор профиля · контекст · размер · chaining).
5. **Дедуп сабагентов** — консервативный: вычищены продублированные блоки конвенций из тел агентов, где
   они уже покрыты скиллами/`_shared/conventions.md`.
6. **Фича приложения** (в `main` и `task2`): история чата (переживает смерть процесса), избранное
   (★-фильтр), export/import JSON + мок-данные. Файловый JSON-стор, Clean+UDF, сборка зелёная (Android+iOS+lint).

## Что дорабатывал после первой версии
- Профили сделал **универсальными** (не привязанными к стеку) — стек-специфику (Dagger→Koin, Cicerone vs Nav3,
  SideEffect vs Event) увёл в `roster.md`, резолвится на создании задачи.
- Пересекающиеся профили — через **chaining** (Design не дублирует Feature, а запускает его; Incident→Bug Fix).
- Добавил **size-awareness** (XS→XL + масштаб команды) на основе `android-team-prompt` / `kmp-team-prompt`.
- **Дедуп** вышел консервативным — большинство «дублей» оказались уже указателями на скиллы либо уникальным
  контентом; реально почищено 3 файла (xbet-kotlin/xbet-compose/alva-kotlin).

## Открытые точки (на пользователе)
- Прогон профилей first-run (Bug Fix + Research) + скриншоты/логи — снимаются вручную на реальном баге/вопросе.
- 2 alva-скилла (`alva-udf-architecture`, `alva-viewmodel`) global ≠ версии в проекте — выбрать эталон.
- Фича — одноэкранная (нет nav-фреймворка); избранное = фильтр, не отдельный экран. При желании — добавить навигацию.

## Где живёт
- Логика (снапшот): `challenge_advanced/task2/{global,profiles,agents,skills}`.
- Живое: `~/.claude/CLAUDE.md`, `~/.claude/profiles/`, `<project>/.claude/` (git-excluded).
- Фича: `feature/chat/` + `docs/mock_chat_history.json`.
