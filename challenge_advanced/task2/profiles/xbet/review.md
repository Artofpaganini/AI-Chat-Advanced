# Профиль: review — xbet

> Контекст **xbet** (`Mobile_Android_OnexBet`); также обслуживает twin **xbet1** (`own_xbet`).
> Android-only · **Dagger 2** · **Cicerone `XPlatformRouter`** · UDF со **SideEffect** · MCP-доки **Context7**.
> Стек/сабагенты — `roster.md`. Общее — `../_shared/orchestration.md` и `../_shared/conventions.md` (не дублировать).

## Назначение / когда активен
**Ревью готовых изменений** — diff / PR / ветка — против корректности, безопасности, перформанса и конвенций.
Триггеры: «отревьюь», «review PR/ветку/diff», «посмотри изменения», «код-ревью», «что не так в этом коммите».
Примеры: «отревьюй текущую ветку», «review PR #123», «глянь diff перед мержем».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | 1 файл / мелкий diff | session-only: 1× `xbet-review-expert` |
| S/M | PR / ветка на фиче | `xbet-review-expert` + консилиум по измерениям (correctness/security/perf/conventions) |
| L/XL | крупный PR, кросс-модульная миграция | full консилиум + SubLead на под-модули, глубина 2 |

## Стадии (DAG)
`gather-diff → multi-dimension-review → adversarial-verify → report`
Переходы: линейно; **`adversarial-verify → multi-dimension-review`** — откат, если верификация вскрыла новую зону/линзу. `report` — терминальная.
Persistent: `./swarm-report/<slug>-review.md` (каждый finding: гипотеза → линзы-проверки → verdict confirmed/refuted → `file:line` + fix).

## Сабагенты по стадиям
| Стадия | Роль (subagent) | Модель | Цель |
|---|---|---|---|
| gather-diff | Bash (@DevOps, *в сессии Team Lead*) | — | собрать diff (`git diff`/`git log`/PR), список тронутых файлов+строк |
| multi-dimension-review | **консилиум `xbet-review-expert` ×4** | sonnet | по измерению каждый (см. ниже), список кандидатов-findings с `file:line` |
| adversarial-verify | `xbet-review-expert` (иная линза) / мейн | opus | опровергнуть каждый finding ≥2 линзами; **сомнение → refuted** |
| report | мейн-оркестратор | sonnet | свести выжившие findings в Critical/Warning/Suggestion |

**Консилиум измерений (multi-dimension-review, одним заходом):**
- **correctness** — логика, edge-cases, null/ошибки, конкурентность, атомарность стейта (`_state.update`).
- **security** — секреты в коде, инъекции, авторизация, небезопасные дефолты (пересекается с security-audit, здесь — по diff).
- **perf** — лишние аллокации/рекомпозиции, N+1, блокирующие вызовы, ненужная работа на hot-path.
- **conventions** — конвенции проекта (`../_shared/conventions.md` + `xbet-project-context`): **visibility = Critical**, нейминг моделей по слою, `_state.update`, SideEffect-паттерн, запрет `!!`/`Any`/«DTO», Cicerone-классы не тронуты.

**Adversarial-verify:** каждый finding проходит ≥2 независимые линзы (перечитать код вокруг, проверить контекст вызова, найти опровержение). По умолчанию **refuted при сомнении** — лучше пропустить спорное, чем зашуметь ложным.

## MCP / Skills (обязательные)
`ast-index` (читать контекст findings — callers/иерархия) · `superpowers:requesting-code-review` (чек-лист) · `xbet-project-context` + `../_shared/conventions.md` · `xbet-udf-architecture` · `xbet-navigation` · Sentry — если diff трогает known-crash зону · **Context7** — при сомнении в API библиотеки.

## MUST (обязан)
- Структурировать вывод строго: **Critical / Warning / Suggestion**.
- **Верифицировать каждый finding** (adversarial-verify, ≥2 линзы) ПЕРЕД выдачей; невыживших — выкинуть.
- Читать контекст через **ast-index** (callers/иерархия/Dagger), а не судить по одной строке diff.
- Каждый пункт — с `file:line` + конкретным предлагаемым fix.
- Visibility-нарушения (дефолтный `public` вместо `internal`) — уровень **Critical**.

## MUST NOT (нельзя)
- **Переписывать/править код** — только предлагать fix текстом (правки — профиль feature/bug-fix).
- **Флагать отсутствие тестов** — тесты в xbet **opt-in** (см. roster) — не считать это дефектом.
- Выдавать неверифицированные findings; шуметь стилистикой поверх Critical/Warning.
- Ревьюить по памяти об API — сверяться с Context7.

## Формат ответа
- **Critical** — блокеры мержа (баг/дыра/visibility/сломанный контракт): `file:line` + причина + fix.
- **Warnings** — сильно желательно поправить: `file:line` + fix.
- **Suggestions** — необязательные улучшения: `file:line` + идея.
Каждый пункт — одной-двумя строками. Пусто в секции — писать «— нет».

## Chaining (если апстрим)
Не апстрим; **conditional-возврат**: найден Critical/Warning → вернуть автору-профилю на фикс —
`Chaining: review → bug-fix` (дефект) · `review → feature` (доработка) · `review → refactor` (структурный запах). Мейн объявляет возврат явно.
