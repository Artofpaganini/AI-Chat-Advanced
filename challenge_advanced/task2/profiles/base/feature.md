# Профиль: feature — base

> Base-тюнинг универсального flow. **Контекст base — кросс-платформа (Android/KMM/Backend), generic-агенты; если проект окажется реальным xbet/alva — переключиться на их roster.**
> Стек/сабагенты — `base/roster.md`; общее — `_shared/orchestration.md` + `_shared/conventions.md` (не дублировать).
> **Направление стека (Android / KMM+CMP / Backend) выбирается на создании задачи** (шпаргалка — `base/roster.md` + глоб. CLAUDE «Стек 2026»).

## Назначение / когда активен
Строим новую функциональность (экран, фича, use-case, интеграция). Главная точка приземления chaining'а.
**Триггеры:** «добавь/сделай/реализуй фичу/экран/кнопку», «нужна возможность…», приходящий на вход
готовый макет / требования / архитектура.
**Примеры:** покрасить кнопку (XS); экран профиля из готовых компонентов (S); авторизация через API (L);
эпик онбординга на 3+ экрана (XL).

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | покрасить кнопку, тултип, строковый ресурс | session-only: `Explore` + 1 исполнитель (@UIDev/@Dev), без консилиума |
| S | +use-case/маппер, экран из готовых компонентов | 1-2 исполнителя последовательно |
| M | кросс-модульная навигация+DI одной фичи | консилиум (research) → @Dev(+@UIDev) → @Reviewer |
| L | фича 1-2 экрана с нуля, API-интеграция | @Architect → @Dev+@UIDev+@BackendDev → @Reviewer, SubLead по надобности |
| XL | эпик 3+ экранов | full team + рекурсивные SubLead (глубина 2); фича режется на vertical-slice'ы |

## Стадии (DAG)
`research → plan → execute → validation → report → done`.
Переходы линейно; из `validation` при провале → назад в `execute` (фикс) или `plan` (дефект проектный).
XS сворачивает research+plan в один проход. Persistent: `./swarm-report/<slug>-feature.md` (план — живой
источник правды на L/XL, перечитывать перед каждым шагом, отмечать `[x]`). Смена стадии: `Переход: <A> → <B>`.

## Сабагенты по стадиям
| Стадия | Роль → агент (base) | Модель | Цель |
|---|---|---|---|
| research | консилиум: @Architect (`Plan`) · @UIDev · @BackendDev · security-линза · @DevOps (`Explore`) | Opus | параллельно, разными линзами: точки интеграции, DI-граф, API, риски; синтез — оркестратор |
| plan | @Architect (`Plan`) | Opus | декомпозиция на изолированные единицы, выбор подхода из 2-3, I/O-контракты |
| execute | @Dev · @UIDev · @BackendDev (`general-purpose`) | Sonnet | реализация по плану мелкими проверяемыми шагами (disjoint-модули → параллельно) |
| validation | @Reviewer (`general-purpose`) + @DevOps (Bash) | Opus/Sonnet | ревью против conventions + зелёная сборка + UI-check через claude-in-mobile |
| report | оркестратор | — | сводка: что / где интегрировано / чем проверено |

**Base-агенты:** @Architect→`Plan`/`general-purpose` · @Dev/@UIDev/@BackendDev/@QA→`general-purpose` · @Reviewer→`general-purpose` (+skill `superpowers:requesting-code-review`) · @Researcher→`Explore` · @DevOps→Bash в сессии. Роль+стек+I/O-контракт — в промпте агента.
Консилиум на research — один заход, разные домены (диверсити важнее избыточности); см. `_shared/orchestration.md`.
Шаг «identify platforms» — по направлению: KMM → Android+iOS parity-проверка; Android-only / Backend — пропустить.

## MCP / Skills (обязательные)
`ast-index` (поиск, без `update`) · `Context7`/DeepWiki (доки/версии, не по памяти) · claude-in-mobile
(прокликать UI) · Sentry (не ломаем ли известные краши) · caveman (компактность).
Skills: `_shared/conventions.md` (модели/слои/UDF/StateFlow/visibility — single source) · `compose-principles` (Compose-направление) ·
`team-lead-orchestration` · `ux-writer-core` (копирайт/ресурсы) · релевантные по направлению (`navigation-3`/`material-3`/`edge-to-edge`/`koin-migration:di-migration`).
Creative-развилки на XS/S — `superpowers:brainstorming` до кода.

## MUST (обязан)
- Следовать `_shared/conventions.md` (visibility, модели по слою, UDF, StateFlow-атомарность, нейминг).
- Сборка зелёная перед `done` (билд направления, напр. `./gradlew :androidApp:assembleDevDebug` для KMM); evidence-before-assertions — не заявлять «работает» без прогона.
- UI-фичу прокликать через claude-in-mobile (реальный экран, не только компиляция).
- Context-passing: каждому сабагенту — исходный запрос + саммари предыдущей стадии + I/O-контракт.

## MUST NOT (нельзя)
- Пропускать `validation` (сборка / ревью / UI-check) — даже под «срочно».
- Добавлять тесты без явной просьбы (тесты **opt-in**; @QA — только по запросу).
- Оверинженерить XS/S — консилиум, SubLead, лишние абстракции на «покрасить кнопку» запрещены.
- Менять смежные фичи «заодно», трогать WIP-файлы пользователя, удалять без явного разрешения.

## Формат ответа
Преамбула `📋 Задача · 📊 Сложность · 📱 Платформы · 👥 Команда · 📐 План`. По завершении: что сделано
(файлы — абсолютные пути) · где интегрировано · чем проверено (сборка + UI-check с выводом) · открытые
вопросы. Код в ответ — только если текст load-bearing.

## Chaining (если апстрим)
**Главный target, не апстрим.** Принимает вход: `design → feature` (макет), `requirements → feature`
(стори+AC), `architecture → feature` (план/контракты). Апстрим-артефакт лежит в `./swarm-report/<slug>-*.md`
и подаётся в `research/plan` как готовый вход — research не дублируется, если апстрим его закрыл. Дальше не
чейнится: терминал `done`.
