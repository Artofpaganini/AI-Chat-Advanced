# PR-Check отчёт (единый L1 + L2) — демонстрация flow

Профиль `pr-check` прогоняет оба уровня и собирает ОДИН отчёт с вердиктом. Ниже — реальный прогон по
приложению AI-Chat-Advanced (ветка `task3`).

## L1 — код-тесты (unit/integration)
Команда: `./gradlew :feature:chat:testAndroidHostTest :feature:ai:testAndroidHostTest`
**Результат: 30 тестов, 30 passed, 0 failed.**

| Модуль | Файл | Тестов |
|---|---|---|
| presentation mapper | `ChatUiMapperTest` | 7 |
| data mappers | `ChatDataMappersTest` | 7 |
| repository (integration, fake datasource) | `ChatHistoryRepositoryImplTest` | 7 |
| domain use-cases | `ChatHistoryUseCasesTest` | 7 |
| feature:ai use-case | `SendMessageUseCaseTest` | 2 |

## L2 — UI smoke (agent сам, через adb, скрин на каждом шаге)
Устройство: эмулятор Small_Phone. **Результат: 5/5 PASS, 0 FATAL.**

| Сценарий | Итог | Скрин |
|---|---|---|
| S1 cold start | ✅ | `smoke/shots/s1_launch.png` |
| S2 send (живой ответ DeepSeek) | ✅ | `s2_typed/s2_sending/s2_reply` |
| S3 favorite + filter | ✅ | `s3_fav/s3_filter/s3_all` |
| S4 export/import JSON | ✅ | `s4_export/s4_import` |
| S5 persistence (после force-stop) | ✅ | `s5_relaunch` |

## Вердикт: ✅ MERGE-READY
L1 зелёный (30/30), L2 зелёный (5/5). Критичный флоу (чат→ответ→избранное→export/import→persistence)
работает вживую, крашей нет.

## Замечания (не блокеры, на решение)
1. `ChatViewModel` не юнит-тестируем без ослабления visibility (`SendMessageUseCase` internal ctor). Фикс — public ctor.
2. import MERGE может сбросить локальный `isFavorite` (imported перекрывает по id). Уточнить семантику.

## Вариация «я задеплоил новую фичу — обнови smoke и прогони заново»
1. Обновить `smoke/scenarios.md` — добавить шаги под новую фичу (новые экраны/действия/поля).
2. Полный прогон: L1 (тесты затронутых модулей) + L2 (обновлённый smoke) → пересобрать этот отчёт.
3. Любой FAIL → `Chaining: pr-check → bug-fix` (прод → `incident`), передать диагноз/скрин/стек.
