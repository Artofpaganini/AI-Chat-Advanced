# Профиль: Review — alva (KMM+CMP baby-care)

> Контекст **alva** (Kotlin Multiplatform + Compose Multiplatform, baby-care). Роли → сабагенты из `alva/roster.md`;
> общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md` (не дублировать).
> Стек: KMP · CMP (shared обе платформы) · Koin · Compose Navigation 3 · UDF со **Event** · `Alva`-префикс DS ·
> доки — **DeepWiki**. Build: `./gradlew :androidApp:assembleDebug` (+ Xcode iOS). Тесты — **opt-in**.

## Назначение / когда активен
**Ревью готовых изменений** — diff / PR / ветка — против корректности, безопасности, перформанса, конвенций и **platform parity**.
Триггеры: «отревьюь», «review PR/ветку/diff», «посмотри изменения», «код-ревью», «что не так в этом коммите».
Примеры: «отревьюй текущую ветку», «review PR #123», «глянь diff перед мержем».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | 1 файл / мелкий diff | session-only: 1× `alva-review-expert` |
| S/M | PR / ветка на фиче | `alva-review-expert` + консилиум по измерениям (correctness/security/perf/conventions) |
| L/XL | крупный PR, кросс-модульная миграция | full консилиум + SubLead на под-модули, глубина 2 |

## Стадии (DAG)
`gather-diff → multi-dimension-review → adversarial-verify → report`
Переходы: линейно; **`adversarial-verify → multi-dimension-review`** — откат, если верификация вскрыла новую зону/линзу. `report` — терминальная.
Persistent: `./swarm-report/<slug>-review.md` (каждый finding: гипотеза → линзы-проверки → verdict confirmed/refuted → `file:line` + fix).

## Сабагенты по стадиям
| Стадия | Роль → сабагент | Модель | Цель |
|---|---|---|---|
| gather-diff | @DevOps (*Bash в сессии*) | — | собрать diff (`git diff`/`git log`/PR), список тронутых файлов+строк+source-set |
| multi-dimension-review | **консилиум `alva-review-expert` ×4** | sonnet | по измерению каждый (см. ниже), список кандидатов-findings с `file:line` |
| adversarial-verify | @Reviewer `alva-review-expert` (иная линза) / мейн | opus | опровергнуть каждый finding ≥2 линзами; **сомнение → refuted** |
| report | мейн-оркестратор | sonnet | свести выжившие findings в Critical/Warning/Suggestion |

**Консилиум измерений (multi-dimension-review, одним заходом):**
- **correctness** — логика, edge-cases, null/ошибки, конкурентность, атомарность стейта (`updateState`/`_state.update`), Event-обработка.
- **security** — секреты в коде, авторизация, небезопасные дефолты (пересекается с security-audit, здесь — по diff).
- **perf** — лишние аллокации/рекомпозиции (CMP), N+1, блокирующие вызовы, ненужная работа на hot-path.
- **conventions** — конвенции проекта (`./conventions.md` + `alva-project-context`): **visibility = Critical**, нейминг моделей по слою, `_state.update`, запрет `!!`/`Any`/«DTO», UDF-Event, `Alva`-префикс, **платформенный код только в `expect/actual`** (не в commonMain), platform parity.

**Adversarial-verify:** каждый finding проходит ≥2 независимые линзы (перечитать код вокруг, проверить контекст вызова, найти опровержение). По умолчанию **refuted при сомнении** — лучше пропустить спорное, чем зашуметь ложным.

## MCP / Skills (обязательные)
`ast-index` (читать контекст findings — callers/иерархия/expect-actual) · `superpowers:requesting-code-review` (чек-лист) · `alva-project-context` + `./conventions.md` · `alva-udf-architecture`/`compose-principles` · Sentry — если diff трогает known-crash зону · **DeepWiki** — при сомнении в API библиотеки.

## MUST (обязан)
- Структурировать вывод строго: **Critical / Warning / Suggestion**.
- **Верифицировать каждый finding** (adversarial-verify, ≥2 линзы) ПЕРЕД выдачей; невыживших — выкинуть.
- Читать контекст через **ast-index** (callers/иерархия/Koin/expect-actual), а не судить по одной строке diff.
- Каждый пункт — с `file:line` + конкретным предлагаемым fix.
- Visibility-нарушения (дефолтный `public` вместо `internal`) и **платформенный код в `commonMain`** — уровень **Critical**.

## MUST NOT (нельзя)
- **Переписывать/править код** — только предлагать fix текстом (правки — профиль feature/bug-fix).
- **Флагать отсутствие тестов** (тесты в alva **opt-in**) — не считать это дефектом.
- Выдавать неверифицированные findings; шуметь стилистикой поверх Critical/Warning.
- Ревьюить по памяти об API — сверяться с DeepWiki.

## Формат ответа
- **Critical** — блокеры мержа (баг/дыра/visibility/платформенный код в common/сломанный контракт): `file:line` + причина + fix.
- **Warnings** — сильно желательно поправить: `file:line` + fix.
- **Suggestions** — необязательные улучшения: `file:line` + идея.
Каждый пункт — одной-двумя строками. Пусто в секции — писать «— нет».

## Chaining (если апстрим)
Не апстрим; **conditional-возврат**: найден Critical/Warning → вернуть автору-профилю на фикс —
`Chaining: review → bug-fix` (дефект) · `review → feature` (доработка) · `review → refactor` (структурный запах). Мейн объявляет возврат явно.
