# Профиль: feature — xbet

> Контекст **xbet** (`Mobile_Android_OnexBet`); также обслуживает twin **xbet1** (`own_xbet`).
> Android-only · Kotlin · Compose/Material3 · **Dagger 2** (+Koin-track) · Coroutines/Flow ·
> **Cicerone `XPlatformRouter`** (не менять) · UDF со **SideEffect** (+Delegates) · `Ds`-префикс · Groovy Gradle · `strings.xml`.
> Стек/сабагенты — `roster.md`. Общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` и `./conventions.md` (не дублировать).

## Назначение / когда активен
Строим новую функциональность (экран, фича, use-case, интеграция). Главная точка приземления chaining'а.
**Триггеры:** «добавь/сделай/реализуй фичу/экран/кнопку», «нужна возможность…», приходящий на вход
готовый макет / требования / архитектура.
**Примеры:** покрасить кнопку (XS); экран профиля из готовых компонентов (S); авторизация через API (L);
эпик онбординга на 3+ экрана (XL).

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | покрасить кнопку, тултип, строковый ресурс | session-only: `Explore` + 1 исполнитель (`xbet-compose-expert`/`xbet-kotlin-expert`), без консилиума |
| S | +use-case/маппер, экран из готовых компонентов | 1-2 исполнителя последовательно |
| M | кросс-модульная навигация+DI одной фичи | консилиум (research) → `xbet-kotlin-expert`(+`xbet-compose-expert`) → `xbet-review-expert` |
| L | фича 1-2 экрана с нуля, API-интеграция | `xbet-planner-expert` → `xbet-kotlin-expert`+`xbet-compose-expert` → `xbet-review-expert`, SubLead по надобности |
| XL | эпик 3+ экранов | full team + рекурсивные SubLead (глубина 2); фича режется на vertical-slice'ы |

## Стадии (DAG)
`research → plan → execute → validation → report → done`.
Переходы линейно; из `validation` при провале → назад в `execute` (фикс) или `plan` (дефект проектный).
XS сворачивает research+plan в один проход. Persistent: `./swarm-report/<slug>-feature.md` (план — живой
источник правды на L/XL, перечитывать перед каждым шагом, отмечать `[x]`). Смена стадии: `Переход: <A> → <B>`.

## Сабагенты по стадиям
| Стадия | Роль (subagent) | Модель | Цель |
|---|---|---|---|
| research | консилиум: `xbet-planner-expert` · `xbet-compose-expert` · `xbet-kotlin-expert` (data/API) · security-линза · Bash (@DevOps) | Opus | параллельно, разными линзами: точки интеграции, Dagger-граф, API, риски; синтез — оркестратор |
| plan | `xbet-planner-expert` | Opus | декомпозиция на изолированные единицы, выбор подхода из 2-3, I/O-контракты |
| execute | `xbet-kotlin-expert` · `xbet-compose-expert` | Sonnet | реализация по плану мелкими проверяемыми шагами (disjoint-модули → параллельно) |
| validation | `xbet-review-expert` + Bash (@DevOps) | Opus/Sonnet | ревью против conventions + `./gradlew assembleBetaDebug` + UI-check через claude-in-mobile |
| report | оркестратор | — | сводка: что / где интегрировано / чем проверено |

Консилиум на research — один заход, разные домены (диверсити важнее избыточности); см. секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md`.
Android-only — шаг «identify platforms» **пропустить**.

## MCP / Skills (обязательные)
`ast-index` (поиск, без `update`) · **Context7** (доки/версии, не по памяти) · claude-in-mobile
(прокликать UI) · Sentry (не ломаем ли известные краши) · caveman (компактность).
Skills: `xbet-project-context` · `xbet-udf-architecture` (SideEffect+Delegates) · `xbet-viewmodel` ·
`xbet-navigation` (Cicerone `XPlatformRouter`) · `xbet-reference-modules` · `compose-principles` (`Ds`-префикс) ·
`team-lead-orchestration` · `ux-writer-core` (`strings.xml`/копирайт).
Creative-развилки на XS/S — `superpowers:brainstorming` до кода.

## MUST (обязан)
- Следовать `./conventions.md` + `xbet-project-context` (visibility, модели по слою, UDF/SideEffect, StateFlow-атомарность, нейминг).
- `./gradlew assembleBetaDebug` зелёный перед `done`; evidence-before-assertions — не заявлять «работает» без прогона.
- UI-фичу прокликать через claude-in-mobile (реальный экран, не только компиляция).
- Context-passing: каждому сабагенту — исходный запрос + саммари предыдущей стадии + I/O-контракт.

## MUST NOT (нельзя)
- Пропускать `validation` (сборка / ревью / UI-check) — даже под «срочно».
- Добавлять тесты без явной просьбы (тесты **opt-in**; `xbet-tester-expert` — только по запросу).
- Менять классы Cicerone / `XPlatformRouter`.
- Оверинженерить XS/S — консилиум, SubLead, лишние абстракции на «покрасить кнопку» запрещены.
- Менять смежные фичи «заодно», трогать WIP-файлы пользователя, удалять без явного разрешения.

## Формат ответа
Преамбула `📋 Задача · 📊 Сложность · 📱 Android · 👥 Команда · 📐 План`. По завершении: что сделано
(файлы — абсолютные пути) · где интегрировано · чем проверено (`assembleBetaDebug` + UI-check с выводом) ·
открытые вопросы. Код в ответ — только если текст load-bearing.

## Chaining (если апстрим)
**Главный target, не апстрим.** Принимает вход: `design → feature` (макет), `requirements → feature`
(стори+AC), `architecture → feature` (план/контракты). Апстрим-артефакт лежит в `./swarm-report/<slug>-*.md`
и подаётся в `research/plan` как готовый вход — research не дублируется, если апстрим его закрыл. Дальше не
чейнится: терминал `done`.
