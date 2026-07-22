# Профиль: Release — base

> Base-тюнинг универсального flow. **Контекст base — кросс-платформа (Android/KMM/Backend), generic-агенты; если проект окажется реальным xbet/alva — переключиться на их roster.**
> Стек/сабагенты — `base/roster.md`; общее — `_shared/orchestration.md` + `_shared/conventions.md` (не дублировать).
> **Направление стека (Android / KMM+CMP / Backend) выбирается на создании задачи** (варианты сборки — по направлению: APK/AAB, iOS archive, Docker image).

## Назначение / когда активен
Подготовить и выпустить релиз/деплой: зелёные гейты → сборка вариантов → публикация → smoke.
Триггеры: «релиз», «выпусти версию», «собери релиз», «задеплой», «выкати в стор/прод», «release notes + публикация».
Примеры: «выпусти 2.4.0 в internal track», «задеплой backend на staging», «собери beta-релиз и отдай QA».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | bump версии + changelog, локальная релиз-сборка | session-only: Bash (@DevOps) |
| S/M | полный release-checklist → сборка вариантов → internal/staging track | @DevOps + @Reviewer (gate) |
| L/XL | мультиплатформенный релиз (Android+iOS), staged rollout, CI-пайплайн | @DevOps + @Reviewer + @TextWriter (notes) + SubLead |

## Стадии (DAG)
`pre-flight → build-variants → deploy → verify`. Persistent-файл `./swarm-report/<slug>-release.md` (release-checklist как живой источник правды).
- **pre-flight:** зелёный build + lint + тесты; bump версии (semver) + changelog/release notes; проверка signing/secrets (из `BuildConfig`/env, не в артефакте).
- **build-variants:** релиз-варианты по направлению (напр. `./gradlew :androidApp:assembleRelease`/`bundleRelease`, iOS archive, backend Docker image); проверка размера/минификации (R8) при необходимости.
- **deploy:** публикация в store/CI/track/registry — **необратимый шаг, требует подтверждения**.
- **verify:** smoke на опубликованном артефакте (установка/запуск, ключевой happy-path; для backend — health/ключевой эндпоинт).

**Переходы:** линейно pre-flight→build-variants→deploy→verify. Красный на любой стадии → стоп, назад в pre-flight (или `Chaining: release → incident|bug-fix` если дефект в коде). Из verify при регрессии → `Chaining: release → incident`.

## Сабагенты по стадиям
| Стадия | Роль → агент (base) | Модель | Цель |
|---|---|---|---|
| pre-flight | @DevOps (Bash) | — | прогнать build+lint+test, собрать статус гейтов |
| pre-flight | @Reviewer (`general-purpose`) | по roster | ревью diff релиза + changelog против конвенций |
| build-variants | @DevOps (Bash) | — | собрать релиз-варианты, зафиксировать артефакты |
| deploy | @DevOps (Bash) | — | публикация после подтверждения |
| verify | @DevOps (Bash) | — | smoke опубликованного артефакта |

**Base-агенты:** @DevOps→Bash в сессии · @Reviewer→`general-purpose` (+skill `superpowers:requesting-code-review`) · @TextWriter→`general-purpose`. Роль+стек+I/O-контракт — в промпте агента.

## MCP / Skills (обязательные)
`ast-index` (что вошло в релиз) · `_shared/conventions.md` (base без project-context-скилла) · `superpowers:verification-before-completion` (evidence before assertions) · `superpowers:finishing-a-development-branch` · по надобности `r8-analyzer` / `agp-9-upgrade` / `play-billing-library-version-upgrade`.

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

## Chaining (если апстрим)
Терминальный по умолчанию. При провале гейта/verify-регрессии → `Chaining: release → incident` (прод) или `release → bug-fix` (pre-prod), передать: упавший гейт/стек, версию, diff релиза.
