# Task 3 — два уровня тестирования (код + UI smoke)

Тестирование текущего приложения (AI-Chat-Advanced) на двух уровнях + интеграция в flow.

## Level 1 — код-тесты (unit/integration на бизнес-логику)
Было 0 тестов. Ассистент сам нашёл непокрытые модули и покрыл их — **5 файлов, 30 тестов, зелёные с первого прогона**.
- `feature/chat/.../presentation/mapper/ChatUiMapperTest.kt` (7) — фильтр избранного, проекция сообщений.
- `feature/chat/.../data/mapper/ChatDataMappersTest.kt` (7) — маппинг data↔domain, round-trip, fallback.
- `feature/chat/.../data/repository/ChatHistoryRepositoryImplTest.kt` (7) — интеграция с fake datasource: save/load, export, import REPLACE/MERGE.
- `feature/chat/.../domain/usecase/ChatHistoryUseCasesTest.kt` (7) — Load/Save/Export/Import (`Result` success/failure).
- `feature/ai/.../domain/usecase/SendMessageUseCaseTest.kt` (2) — success/failure.

Прогон: `./gradlew :feature:chat:testAndroidHostTest :feature:ai:testAndroidHostTest` → **30 passed**.
Инфра: turbine + coroutines-test в commonTest; включён `withHostTest{}` (иначе KMP-тесты шли только на iOS-симулятор).

**Продовые находки при тестировании:**
1. `ChatViewModel` не юнит-тестируем без ослабления visibility (`SendMessageUseCase` internal ctor + internal `AiRepository`) — покрыл use-case в `feature:ai`. Фикс: сделать ctor public.
2. import MERGE может сбросить локальный favorite (imported перекрывает по id) — зафиксировано тестом, флаг на решение.

## Level 2 — UI smoke (agent сам протыкивает через adb)
Тулинг: mobile-MCP не подключён, web-таргета нет → драйвер **adb** по эмулятору (реальные тапы + `screencap`).
Сценарии MCP-ready (те же шаги гонит `claude-in-mobile`).
- `smoke/scenarios.md` — 5 сценариев (cold start · отправка · избранное+фильтр · export/import · persistence).
- `smoke/run_smoke.sh` — adb-раннер (install→launch→сценарии→скрины→report).
- `smoke/report.md` — **5/5 PASS**, скрины `smoke/shots/*.png` на каждом шаге.
- Реальный прогон на эмуляторе Small_Phone: S2 получил живой ответ DeepSeek, S5 подтвердил persistence после `force-stop`.

## Flow-интеграция
Профиль **`pr-check`** (`pr-check.md` — копия в снапшоте; в системе живёт в каждом каталоге: `~/.claude/profiles/{base,xbet,alva}/pr-check.md`):
после PR/деплоя → прогнать L1 (код-тесты затронутых модулей) + L2 (smoke) → **единый отчёт** → вердикт
MERGE-READY/BLOCKED. Любой FAIL → chaining в `bug-fix`/`incident`.
Вариация «я задеплоил фичу — обнови smoke и прогони заново»: сперва апдейт `smoke/scenarios.md` под новую
фичу, затем полный прогон L1+L2.

## Итог
Код-тесты на 5 модулей (30, зелёные) + 5 smoke-сценариев (agent прогнал сам через adb, 5/5 PASS, скрины) +
интеграция в dev-flow (профиль `pr-check`). Ветка `task3`.
