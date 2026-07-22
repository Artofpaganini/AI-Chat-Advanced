# Профиль: Docs — alva (KMM+CMP baby-care)

> Контекст **alva** (Kotlin Multiplatform + Compose Multiplatform, baby-care). Роли → сабагенты из `alva/roster.md`;
> общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` + `./conventions.md` (не дублировать).
> Стек: KMP · CMP (shared UI обе платформы) · Koin · Compose Navigation 3 · UDF со **Event** · `Alva`-префикс DS ·
> `composeResources/` · доки — **DeepWiki**. Build: `./gradlew :androidApp:assembleDebug` (+ Xcode iOS).

## Назначение / когда активен
Написать/обновить документацию: README, ADR, KDoc (где разрешено политикой), release notes, гайды/онбординг.
Триггеры: «напиши README», «задокументируй», «ADR по решению», «release notes», «гайд по фиче/модулю».
Примеры: «README для `core:navigation`», «ADR: почему Compose Navigation 3», «онбординг-гайд по KMP-проекту».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | правка раздела README / release notes | session-only: `alva-writer-expert` |
| S/M | новый README/ADR/гайд фичи | `Explore` (gather) → `alva-writer-expert` → `alva-review-expert` (accuracy) |
| L/XL | набор доков: арх-обзор + серия ADR + онбординг | full team: консилиум-`Explore` → `alva-writer-expert` → `alva-review-expert`, SubLead |

## Стадии (DAG)
`scope → gather → write → verify`. Persistent-файл `./swarm-report/<slug>-docs.md` (аутлайн + список источников).
- **scope:** что за документ, аудитория, границы (что НЕ документируем); аутлайн.
- **gather:** читать РЕАЛЬНЫЙ код (`ast-index`: символы/сигнатуры/usages, в т.ч. `expect/actual`), внешние API — DeepWiki. Собрать факты, не по памяти.
- **write:** текст по `ux-writer-core`; KDoc — только по политике; примеры кода — минимальные и корректные (KMP-совместимые).
- **verify:** ссылки живые, сигнатуры/факты совпадают с кодом, примеры собираются/сверены.

**Переходы:** scope→gather→write→verify линейно. На verify нашли расхождение с кодом → назад в gather (перечитать), не «подгонять» текст. Изменился scope → назад в scope.

## Сабагенты по стадиям
| Стадия | Роль → сабагент | Модель | Цель |
|---|---|---|---|
| gather | @Researcher `Explore` | по roster | вытащить реальные сигнатуры/структуру/usages (commonMain + платформенное) |
| write | @TextWriter `alva-writer-expert` (+ skill `ux-writer-core`) | по roster | написать документ в фирменном стиле |
| verify | @Reviewer `alva-review-expert` | по roster | сверить точность с кодом, ссылки, сборку примеров |

## MCP / Skills (обязательные)
`ux-writer-core` (**обязателен** для @TextWriter) · `ast-index` (читать реальный код) · **DeepWiki** (внешние API/версии KMP/Koin/Compose — не по памяти) · `alva-project-context`.

## MUST (обязан)
- **Точность:** читать реальный код, брать фактические сигнатуры/имена/пути; не выдумывать. Для KMP — отмечать, где `commonMain`, где `expect/actual`.
- Следовать `ux-writer-core` (стиль/структура/ресурс-строки).
- **KDoc-политика (Alva):** документировать только уникальные кейсы — навигация / кастомный UI / нетривиальная логика / публичный API; **новый KDoc/комментарии — по-русски, идентификаторы английские**.
- Примеры кода — компилируемые/сверенные с кодом.
- Ссылки/якоря — рабочие.

## MUST NOT (нельзя)
- Выдумывать API/сигнатуры/поведение.
- Документировать стандартный самоочевидный код (геттеры, тривиальные data class).
- Писать KDoc без нужды (вне политики) / незапрошенные комментарии.
- Трогать существующие комментарии с опечатками.

## Формат ответа
Что задокументировано и где (пути), какие источники прочитаны (файлы/символы), verify-итог (ссылки ✅, сигнатуры сверены ✅, примеры собраны ✅).

## Chaining (если апстрим)
Терминальный. Не запускает исполнительные профили.
