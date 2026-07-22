# Профиль: bug-fix — xbet

> Контекст **xbet** (`Mobile_Android_OnexBet`); также обслуживает twin **xbet1** (`own_xbet`).
> Android-only · Kotlin · Compose · **Dagger 2** (+Koin-track) · **Cicerone `XPlatformRouter`** (не менять) ·
> UDF со **SideEffect** (+Delegates) · Build `./gradlew assembleBetaDebug` · `strings.xml`.
> Стек/сабагенты — `roster.md`. Общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` и `./conventions.md` (не дублировать).

## Назначение / когда активен
Починка дефекта/краша с обязательным воспроизведением. Точка приземления chaining'а от `incident`.
**Триггеры:** «баг», «краш», «не работает», «падает», «ошибка», Sentry-issue, репорт с шагами.
**Примеры:** NPE в условии (XS); неверный стейт экрана (S); гонка/утечка стейта (M); регрессия по площади (XL).

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | однострочный/очевидный (NPE, опечатка в условии) | session-only: `Explore` + 1 исполнитель |
| S | локальный баг в одном слое | `xbet-kotlin-expert`/`xbet-compose-expert` → `xbet-review-expert` |
| M | кросс-слойный / race / рассинхрон стейта | консилиум-diagnose → `xbet-kotlin-expert` → `xbet-review-expert` |
| L | системный дефект, несколько модулей | `xbet-planner-expert` + консилиум → `xbet-kotlin-expert`(+`xbet-compose-expert`) → `xbet-review-expert` |
| XL | прод-инцидент, регрессия по площади | full team + SubLead, hotfix-ветка |

## Стадии (DAG)
`reproduce → diagnose → fix → validation → report → done`.
Переходы: `reproduce` провалился 3× → статус «не воспроизводится» (стоп, вернуть запросившему с логом
попыток, НЕ чинить вслепую); `diagnose → fix`; `validation` при провале → назад в `fix` (плохой фикс) или
`diagnose` (неверный корень). Persistent: `./swarm-report/<slug>-reproduce.md` (шаги, окружение, стек,
гипотезы) — перечитывать перед каждым действием, отмечать `[x]`.

## Сабагенты по стадиям
| Стадия | Роль (subagent) | Модель | Цель |
|---|---|---|---|
| reproduce | `Explore`/`xbet-kotlin-expert` + Bash (@DevOps) | Sonnet | воспроизвести по репорту/Sentry; зафиксировать шаги+окружение в `-reproduce.md` |
| diagnose | консилиум: diagnostics-линза · `xbet-planner-expert` · security-линза · Bash | Opus | параллельно локализовать корень: стек, дифф, гонки, конфиг; синтез — оркестратор |
| fix | `xbet-kotlin-expert` · `xbet-compose-expert` | Sonnet | минимальный фикс корня (не симптома), по conventions |
| validation | `xbet-review-expert` + Bash (@DevOps) | Opus/Sonnet | `assembleBetaDebug` + regression: сценарий больше не падает, существующие тесты целы |
| report | оркестратор | — | воспроизведение / корень / фикс / доказательство regression |

## MCP / Skills (обязательные)
`superpowers:systematic-debugging` (обязательно, до правки) · `ast-index` (стек/usages/callers) · **Sentry**
(событие, частота, стек, релиз) · **Context7** (доки) · claude-in-mobile (воспроизвести UI-баг) · caveman.
Skills: `xbet-project-context` · `xbet-udf-architecture` · `xbet-viewmodel` · `xbet-navigation` · `compose-principles`.

## MUST (обязан)
- Сначала воспроизвести: до 3 попыток; не удалось — статус «не воспроизводится» с логом попыток, дальше НЕ чинить.
- Читать Sentry-событие(я) + логи ДО диагноза; найти корень и чинить именно его.
- Regression-проверка в `validation`: исходный сценарий больше не падает **и** существующие тесты остаются зелёными.
- Вести `-reproduce.md`: перечитывать перед каждым шагом, отмечать выполненное.

## MUST NOT (нельзя)
- Чинить без воспроизведения и без установленного корня (диагноза).
- Игнорировать / ослаблять / удалять существующие тесты ради «зелёного».
- Глушить симптом (try/catch, скрытие поля) вместо устранения корня.
- Менять классы Cicerone / `XPlatformRouter` под видом фикса.
- Добавлять НОВЫЕ тесты без явной просьбы (opt-in); при этом существующие обязаны остаться зелёными.

## Формат ответа
Воспроизведение (шаги + окружение) · корень (файл:строка, почему) · фикс (что изменено, файлы — абсолютные
пути) · доказательство regression (сценарий + вывод `assembleBetaDebug`/тестов). Код — только если load-bearing (сам баг).

## Chaining (если апстрим)
**Downstream от `incident`:** `incident → bug-fix` (urgent). На входе — прод-краш + Sentry-контекст; `reproduce`
стартует с прод-сигнала (ускоренный путь, hotfix-ветка). Дальше не чейнится: терминал `done`.
