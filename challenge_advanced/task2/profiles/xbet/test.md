# Профиль: test — xbet

> Контекст **xbet** (`Mobile_Android_OnexBet`); также обслуживает twin **xbet1** (`own_xbet`).
> Android-only · UDF (`UdfBaseViewModel`/`UdfBaseDelegate`) со **SideEffect** · **Cicerone `XPlatformRouter`** · Build `./gradlew assembleBetaDebug`.
> Стек/сабагенты — `roster.md`. Общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` и `./conventions.md` (не дублировать).

## Назначение / когда активен
**Написать/улучшить тесты и покрытие. OPT-IN — активируется ТОЛЬКО по явной просьбе** («тесты», «coverage», «покрой тестами»).
Триггеры (строго явные): «напиши тесты на …», «подними покрытие …», «протести …», «coverage для …».
Примеры: «напиши unit-тесты на LoginViewModel», «покрой тестами маппер X», «coverage на data-слой фичи».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | 1 маппер / 1 use-case | session-only: 1× `xbet-tester-expert` |
| S/M | ViewModel + data-слой фичи | `xbet-tester-expert` (план по слоям) → run |
| L/XL | покрытие всей фичи/эпика | несколько `xbet-tester-expert` параллельно на **disjoint слоях** (presentation/domain/data) + сведение мейном |

## Стадии (DAG)
`identify-gaps → plan → write → run`
Переходы: линейно; **`run → write`** — откат при красных/флаки-тестах (фикс теста); **`run → identify-gaps`** — если вскрылся непокрытый кейс. `run` (зелёные) — терминальная.
Persistent: `./swarm-report/<slug>-test.md` (матрица «класс × поле × кейс», статус `[x]`/red/green).

## Сабагенты по стадиям
| Стадия | Роль (subagent) | Модель | Цель |
|---|---|---|---|
| identify-gaps | `Explore` / `xbet-tester-expert` | sonnet | найти непокрытые классы/ветки, собрать сигнатуры и зависимости под моки |
| plan | `xbet-tester-expert` / мейн | sonnet | план по слоям: что мокать, какие кейсы на каждое поле/ветку |
| write | **`xbet-tester-expert`** | sonnet | тесты по тест-конвенциям xbet, один класс — один тест-файл |
| run | Bash (@DevOps) / `xbet-tester-expert` | — | прогнать таргет-модуль, довести до зелёного, приложить вывод |

Параллелят на L/XL: `xbet-tester-expert` на disjoint слоях (presentation / domain / data), сборку и прогон — один раз, сведение мейном.

## MCP / Skills (обязательные)
`xbet-testing` · `xbet-viewmodel` (тест-инфра проекта) · `ast-index` (сигнатуры/зависимости тестируемого) · `superpowers:test-driven-development` (при новом коде) · **Context7** — API тест-либы.
**Тест-конвенции xbet:** JUnit5 + MockK + **FlowTestResultHandler** (`flow.handleTest(scope)` + `.finish()`, никогда `first()`/`toList()`) + **verifyRouter**/`verifyRouterOrder`/`verifyRouterSequence`; `TestCoroutinesInitializer` + `TestCoroutineDispatchers`; `UdfBaseViewModel` — driving через `onAction(Action.Ui/Internal.X)`, State через `viewModel.state.<field>`, SideEffect через `getSideEffect().handleTest(this)`.

## MUST (обязан)
- **Следовать тест-конвенциям xbet** из `xbet-testing` (не изобретать свой стиль): Flow — только через FlowTestResultHandler, роутер — через verifyRouter.
- **Запустить тесты** и довести до зелёного; приложить реальный вывод прогона (evidence before assertions).
- Покрыть **каждое поле** и **каждую ситуацию**: success / success-empty / server-error / client-error (+ edge-ветки).
- Один тестируемый класс — отдельный тест-файл; моки через инжекцию, диспетчеры — тестовые.

## MUST NOT (нельзя)
- **Запускаться без явной просьбы** пользователя на тесты/coverage (opt-in; не авто-хвост feature/bug-fix).
- **Трогать прод-код** сверх минимально необходимого для тестируемости (и такое — согласовать/пометить).
- Проверять Flow через `first()`/`toList()` — только через `flow.handleTest(scope)`.
- Заявлять «зелено», не прогнав; коммитить/пушить без явной просьбы.

## Формат ответа
- **Файлы тестов** — абсолютные пути, что покрывает каждый.
- **Матрица покрытия** — класс × поле/ветка × кейс (success/empty/server/client), галочки.
- **Прогон** — команда сборки/теста + итог (passed/failed, кол-во), при красных — вывод и причина.
- **Пробелы** — что осознанно не покрыто и почему.

**Маркировка прогресса — обязательна на каждом шаге task execution:**
- **Старт шага:** `▶️ **ШАГ <n>/<N> · <стадия>** — <название шага>`
- **Задача шага:** `🎯 **Задача:** <что именно делаем — одна строка>`
- **Итог шага:** `✅ **Итог:** <главная мысль>` · провал — `❌ **Провал:** <что сломалось + где>` · частично — `⚠️ **Частично:** <что осталось>`
- **Переход стадии:** `🔀 **Переход:** <стадия> → <стадия>` · чейнинг — `⛓️ **Chaining:** <profile> → <profile>`

Каждая метка — отдельной строкой, иконка + **жирный** лейбл, не сливать с прозой. Между шагами — `---`.
Без маркировки шаг считается незакрытым.

## Chaining (если апстрим)
Не апстрим; downstream-профиль. Обычно завершает цепочку `feature|bug-fix → test` (по явному запросу). Красный, вскрывший баг продукта → `Chaining: test → bug-fix`.
