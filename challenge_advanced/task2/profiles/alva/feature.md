# Профиль: feature — alva (KMM+CMP baby-care)

> Контекст **alva** (Kotlin Multiplatform + Compose Multiplatform, baby-care). Роли → сабагенты из `alva/roster.md`;
> общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md` (не дублировать).
> Стек: KMP · CMP (shared UI служит Android И iOS) · Koin · Compose Navigation 3 · UDF со **Event** · `Alva`-префикс DS ·
> Kotlin DSL + convention-plugins + version catalog · `composeResources/` · доки — **DeepWiki**. Build: `./gradlew :androidApp:assembleDebug` (+ Xcode iOS).

## Назначение / когда активен
Строим новую функциональность (экран, фича, use-case, интеграция). Главная точка приземления chaining'а.
**Триггеры:** «добавь/сделай/реализуй фичу/экран/кнопку», «нужна возможность…», приходящий на вход
готовый макет / требования / архитектура.
**Примеры:** покрасить кнопку (XS); экран профиля ребёнка из готовых `Alva`-компонентов (S); авторизация через Ktor-API (L);
эпик онбординга на 3+ экрана (XL).

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | покрасить кнопку, тултип, строковый ресурс | session-only: `Explore` + 1 исполнитель (`alva-android-ui-expert`/`alva-kotlin-expert`), без консилиума |
| S | +use-case/маппер, экран из готовых компонентов | 1-2 исполнителя последовательно |
| M | кросс-модульная навигация (Nav 3) + Koin одной фичи | консилиум (research) → `alva-kotlin-expert`(+`alva-android-ui-expert`) → `alva-review-expert` |
| L | фича 1-2 экрана с нуля, Ktor-интеграция | `alva-planner-expert` → `alva-kotlin-expert`+`alva-android-ui-expert`(+`alva-ios-ui-expert` если натив) → `alva-review-expert`, SubLead по надобности |
| XL | эпик 3+ экранов | full team + рекурсивные SubLead (глубина 2); фича режется на vertical-slice'ы (domain+data+UI+expect/actual в одной задаче) |

## Стадии (DAG)
`research → identify-platforms → plan → execute → validation → report → done`.
Переходы линейно; из `validation` при провале → назад в `execute` (фикс) или `plan` (дефект проектный).
XS сворачивает research+plan в один проход. Persistent: `./swarm-report/<slug>-feature.md` (план — живой
источник правды на L/XL, перечитывать перед каждым шагом, отмечать `[x]`). Смена стадии: `Переход: <A> → <B>`.

## Сабагенты по стадиям
| Стадия | Роль → сабагент | Модель | Цель |
|---|---|---|---|
| research | консилиум: @Architect `alva-planner-expert` · @UIDev `alva-android-ui-expert` · @BackendDev `alva-kotlin-expert` · security-линза · @DevOps | Opus | параллельно, разными линзами: точки интеграции, Koin-граф, Ktor-API, риски; синтез — оркестратор |
| plan | @Architect `alva-planner-expert` | Opus | декомпозиция на изолированные единицы (vertical-slice), выбор подхода из 2-3, I/O-контракты |
| execute | @Dev `alva-kotlin-expert` · @UIDev `alva-android-ui-expert` (shared Compose) · @IosUiDev `alva-ios-ui-expert` (только натив iOS) | Sonnet | реализация по плану мелкими проверяемыми шагами (disjoint-модули → параллельно) |
| validation | @Reviewer `alva-review-expert` + @DevOps (Bash) | Opus/Sonnet | ревью против conventions + зелёная сборка (`:androidApp:assembleDebug` + iOS/Xcode) + UI-check |
| report | оркестратор | — | сводка: что / где интегрировано / чем проверено / на каких платформах |

Консилиум на research — один заход, разные домены (диверсити важнее избыточности); см. `../orchestration.md`.
**Шаг «identify platforms» — ВКЛючён (KMM):** решить, что в `commonMain` (shared UI+логика на обе платформы), что через `expect/actual`; проверить **platform parity**. Обычный экран = **один shared Compose** (@AndroidUiDev), НЕ плодить @IosUiDev параллельно.

## MCP / Skills (обязательные)
`ast-index` (поиск, без `update`) · **DeepWiki** (доки KMP/Koin/Compose/Nav3, не по памяти) · claude-in-mobile
(прокликать UI) · Sentry (не ломаем ли известные краши) · caveman (компактность).
Skills: `alva-project-context` · `alva-udf-architecture` (Event) · `alva-viewmodel` ·
`navigation-3` · `compose-principles` · `team-lead-orchestration` · `ux-writer-core` (копирайт/`composeResources`).
Creative-развилки на XS/S — `superpowers:brainstorming` до кода.

## MUST (обязан)
- Следовать `../conventions.md` (visibility, модели по слою `*ResponseModel`/`*Model`/`*UiModel`, UDF-Event, StateFlow-атомарность, нейминг).
- **Identify platforms + parity:** платформенный код только через `expect/actual`; в `commonMain` — платформо-нейтрально; фича доступна на Android И iOS.
- Сборка зелёная перед `done` (`:androidApp:assembleDebug`, iOS/Xcode при изменении shared); evidence-before-assertions — не заявлять «работает» без прогона.
- UI-фичу прокликать через claude-in-mobile (реальный экран, не только компиляция).
- Context-passing: каждому сабагенту — исходный запрос + саммари предыдущей стадии + I/O-контракт.

## MUST NOT (нельзя)
- Пропускать `validation` (сборка / ревью / UI-check) — даже под «срочно».
- Класть платформенный код в `commonMain`; плодить `alva-ios-ui-expert` на обычный shared-экран.
- Добавлять тесты без явной просьбы (тесты **opt-in**; @QA `general-purpose` — только по запросу).
- Оверинженерить XS/S — консилиум, SubLead, лишние абстракции на «покрасить кнопку» запрещены.
- Менять смежные фичи «заодно», трогать WIP-файлы пользователя, удалять без явного разрешения.

## Формат ответа
Преамбула `📋 Задача · 📊 Сложность · 📱 Платформы(KMM) · 👥 Команда · 📐 План`. По завершении: что сделано
(файлы — абсолютные пути) · где интегрировано · чем проверено (сборка + UI-check с выводом, платформы) · открытые
вопросы. Код в ответ — только если текст load-bearing.

**Маркировка прогресса — обязательна на каждом шаге task execution:**
- **Старт шага:** `▶️ **ШАГ <n>/<N> · <стадия>** — <название шага>`
- **Задача шага:** `🎯 **Задача:** <что именно делаем — одна строка>`
- **Итог шага:** `✅ **Итог:** <главная мысль>` · провал — `❌ **Провал:** <что сломалось + где>` · частично — `⚠️ **Частично:** <что осталось>`
- **Переход стадии:** `🔀 **Переход:** <стадия> → <стадия>` · чейнинг — `⛓️ **Chaining:** <profile> → <profile>`

Каждая метка — отдельной строкой, иконка + **жирный** лейбл, не сливать с прозой. Между шагами — `---`.
Без маркировки шаг считается незакрытым.

## Chaining (если апстрим)
**Главный target, не апстрим.** Принимает вход: `design → feature` (макет), `requirements → feature`
(стори+AC), `architecture → feature` (план/контракты). Апстрим-артефакт лежит в `./swarm-report/<slug>-*.md`
и подаётся в `research/plan` как готовый вход — research не дублируется, если апстрим его закрыл. Дальше не
чейнится: терминал `done`.
