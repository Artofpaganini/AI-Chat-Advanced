# Профиль: Release — alva (KMM+CMP baby-care)

> Контекст **alva** (Kotlin Multiplatform + Compose Multiplatform, baby-care). Роли → сабагенты из `alva/roster.md`;
> общее — `_shared/orchestration.md` + `_shared/conventions.md` (не дублировать).
> Стек: KMP · CMP (shared обе платформы) · Koin · Compose Navigation 3 · UDF со **Event** · `Alva`-префикс DS ·
> Kotlin DSL + convention-plugins + version catalog · доки — **DeepWiki**. Build: `./gradlew :androidApp:assembleDebug` (Android) + **Xcode archive** (iOS).

## Назначение / когда активен
Подготовить и выпустить релиз/деплой обеих платформ: зелёные гейты → сборка вариантов (Android + iOS) → публикация → smoke.
Триггеры: «релиз», «выпусти версию», «собери релиз», «задеплой», «выкати в стор», «release notes + публикация».
Примеры: «выпусти 2.4.0 в internal track (Play + TestFlight)», «собери beta и отдай QA».

## Размер (XS→XL) → масштаб команды
| Размер | Пример этого профиля | Команда |
|---|---|---|
| XS | bump версии + changelog, локальная релиз-сборка | session-only: Bash (@DevOps) |
| S/M | полный release-checklist → сборка вариантов → internal track (Play/TestFlight) | @DevOps + `alva-review-expert` (gate) |
| L/XL | мультиплатформенный релиз (Android+iOS), staged rollout, CI-пайплайн | @DevOps + `alva-review-expert` + `alva-writer-expert` (notes) + SubLead |

## Стадии (DAG)
`pre-flight → build-variants → deploy → verify`. Persistent-файл `./swarm-report/<slug>-release.md` (release-checklist как живой источник правды).
- **pre-flight:** зелёный build (`:androidApp:assembleDebug` + iOS/Xcode) + lint + тесты; bump версии (semver) + changelog/release notes; проверка signing/secrets (из `local.properties`/`BuildConfig`/env, не в артефакте).
- **build-variants:** релиз-варианты — Android release (App Bundle) + **iOS archive (Xcode/CocoaPods/SPM)**; проверка размера/минификации при необходимости.
- **deploy:** публикация в Play/TestFlight/CI/track — **необратимый шаг, требует подтверждения**.
- **verify:** smoke на опубликованном артефакте (установка/запуск, ключевой happy-path) на обеих платформах.

**Переходы:** линейно pre-flight→build-variants→deploy→verify. Красный на любой стадии → стоп, назад в pre-flight (или `Chaining: release → incident|bug-fix` если дефект в коде). Из verify при регрессии → `Chaining: release → incident`.

## Сабагенты по стадиям
| Стадия | Роль → сабагент | Модель | Цель |
|---|---|---|---|
| pre-flight | @DevOps (Bash) | — | прогнать build+lint+test (Android+iOS), собрать статус гейтов |
| pre-flight | @Reviewer `alva-review-expert` | по roster | ревью diff релиза + changelog против конвенций |
| build-variants | @DevOps (Bash) | — | собрать Android bundle + iOS archive, зафиксировать артефакты |
| deploy | @DevOps (Bash) | — | публикация после подтверждения |
| verify | @DevOps (Bash) | — | smoke опубликованного артефакта (обе платформы) |

## MCP / Skills (обязательные)
`ast-index` (что вошло в релиз) · `alva-project-context` · `superpowers:verification-before-completion` (evidence before assertions) · `superpowers:finishing-a-development-branch` · по надобности `agp-9-upgrade` / `play-billing-library-version-upgrade` · **DeepWiki**.

## MUST (обязан)
- **Все гейты зелёные ДО релиза:** build + lint + тесты пройдены на **обеих платформах** (реальный прогон, не на слово).
- Bump версии + актуальный changelog/release notes (`composeResources`-строки, если пользовательские).
- Вести release-checklist в persistent-файле, отмечать `[x]`.
- **Подтверждать перед необратимым push в store (Play/TestFlight)** (наружу — durable-авторизация обязательна).
- Signing-ключи/secrets — из `local.properties`/`BuildConfig`/env, никогда не в артефакте/коммите.

## MUST NOT (нельзя)
- Деплоить на красном (любой упавший гейт, любая платформа).
- Пропускать гейты ради скорости; релизить одну платформу, забыв про parity другой.
- Тихо релизить/публиковать без явного подтверждения.
- Хардкодить signing/secrets, коммитить keystore.

## Формат ответа
Чеклист гейтов (build Android/iOS/lint/test — ✅/❌ с доказательством), версия + changelog-дельта, список артефактов (пути), статус деплоя (ожидает подтверждения / опубликовано), verify-smoke результат по платформам.

## Chaining (если апстрим)
Терминальный по умолчанию. При провале гейта/verify-регрессии → `Chaining: release → incident` (прод) или `release → bug-fix` (pre-prod), передать: упавший гейт/стек, версию, платформу, diff релиза.
