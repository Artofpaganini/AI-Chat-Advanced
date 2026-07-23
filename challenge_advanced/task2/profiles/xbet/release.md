# Профиль: release — xbet

> Контекст **xbet** (`Mobile_Android_OnexBet`); также обслуживает twin **xbet1** (`own_xbet`).
> Android-only · Build `./gradlew assembleBetaDebug` (+release-варианты) · R8 · signing/secrets из `local.properties`/`BuildConfig`/env.
> Стек/сабагенты — `roster.md`. Общее — секции «Оркестрация»/«Стадии»/«Профили» глобального `~/.claude/CLAUDE.md` и `./conventions.md` (не дублировать).

## Назначение / когда активен
Подготовить и выпустить релиз/деплой: зелёные гейты → сборка вариантов → публикация → smoke.
Триггеры: «релиз», «выпусти версию», «собери релиз», «задеплой», «выкати в стор/прод», «release notes + публикация».
Примеры: «выпусти 2.4.0 в internal track», «собери beta-релиз и отдай QA».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | bump версии + changelog, локальная релиз-сборка | session-only: Bash (@DevOps) |
| S/M | полный release-checklist → сборка вариантов → internal track | Bash (@DevOps) + `xbet-review-expert` (gate) |
| L/XL | релиз со staged rollout, CI-пайплайн | Bash (@DevOps) + `xbet-review-expert` + `xbet-writer-expert` (notes) + SubLead |

## Стадии (DAG)
`pre-flight → build-variants → deploy → verify`. Persistent-файл `./swarm-report/<slug>-release.md` (release-checklist как живой источник правды).
- **pre-flight:** зелёный `assembleBetaDebug` + lint + тесты; bump версии (semver) + changelog/release notes; проверка signing/secrets (из `BuildConfig`/env, не в артефакте).
- **build-variants:** релиз-варианты (`assembleBetaDebug`/release-flavor); проверка размера/минификации (R8) при необходимости.
- **deploy:** публикация в store/CI/track — **необратимый шаг, требует подтверждения**.
- **verify:** smoke на опубликованном артефакте (установка/запуск, ключевой happy-path).

**Переходы:** линейно pre-flight→build-variants→deploy→verify. Красный на любой стадии → стоп, назад в pre-flight (или `Chaining: release → incident|bug-fix` если дефект в коде). Из verify при регрессии → `Chaining: release → incident`.

## Сабагенты по стадиям
| Стадия | Роль (subagent) | Модель | Цель |
|---|---|---|---|
| pre-flight | Bash (@DevOps) | — | прогнать build+lint+test, собрать статус гейтов |
| pre-flight | `xbet-review-expert` | по roster | ревью diff релиза + changelog против конвенций |
| build-variants | Bash (@DevOps) | — | собрать релиз-варианты, зафиксировать артефакты |
| deploy | Bash (@DevOps) | — | публикация после подтверждения |
| verify | Bash (@DevOps) | — | smoke опубликованного артефакта |

## MCP / Skills (обязательные)
`ast-index` (что вошло в релиз) · `xbet-project-context` · `superpowers:verification-before-completion` (evidence before assertions) · `superpowers:finishing-a-development-branch` · по надобности `r8-analyzer` / `agp-9-upgrade` / `play-billing-library-version-upgrade`.

## MUST (обязан)
- **Все гейты зелёные ДО релиза:** build + lint + тесты пройдены (реальный прогон, не на слово).
- Bump версии + актуальный changelog/release notes.
- Вести release-checklist в persistent-файле, отмечать `[x]`.
- **Подтверждать перед необратимым push в store/prod** (наружу — durable-авторизация обязательна).
- Signing-ключи/secrets — из `local.properties`/`BuildConfig`/env, никогда не в артефакте/коммите.

## MUST NOT (нельзя)
- Деплоить на красном (любой упавший гейт).
- Пропускать гейты ради скорости.
- Тихо релизить/публиковать без явного подтверждения.
- Хардкодить signing/secrets, коммитить keystore.

## Формат ответа
Чеклист гейтов (build/lint/test — ✅/❌ с доказательством), версия + changelog-дельта, список артефактов (пути), статус деплоя (ожидает подтверждения / опубликовано), verify-smoke результат.

**Маркировка прогресса — обязательна на каждом шаге task execution:**
- **Старт шага:** `▶️ **ШАГ <n>/<N> · <стадия>** — <название шага>`
- **Задача шага:** `🎯 **Задача:** <что именно делаем — одна строка>`
- **Итог шага:** `✅ **Итог:** <главная мысль>` · провал — `❌ **Провал:** <что сломалось + где>` · частично — `⚠️ **Частично:** <что осталось>`
- **Переход стадии:** `🔀 **Переход:** <стадия> → <стадия>` · чейнинг — `⛓️ **Chaining:** <profile> → <profile>`

Каждая метка — отдельной строкой, иконка + **жирный** лейбл, не сливать с прозой. Между шагами — `---`.
Без маркировки шаг считается незакрытым.

## Chaining (если апстрим)
Терминальный по умолчанию. При провале гейта/verify-регрессии → `Chaining: release → incident` (прод) или `release → bug-fix` (pre-prod), передать: упавший гейт/стек, версию, diff релиза.
