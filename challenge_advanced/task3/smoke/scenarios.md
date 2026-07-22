# Smoke-сценарии (L2) — AI-Chat-Advanced

Приложение одноэкранное (Compose Material3): `ChatScreen` — TopAppBar («Jarvis» + ★-фильтр избранного),
список сообщений (bubbles), input-бар (поле + 🎤 mic + Send), действия export/import, ★ на assistant-бабле.

Драйвер прогона: **adb** по Android-эмулятору (реальные тапы через `uiautomator dump` + bounds, ввод
`input text`, скрин `screencap` на каждом шаге). Сценарии также MCP-ready — те же шаги гонит
`claude-in-mobile` при подключении. Пакет: `com.jarvis.chat` (flavor dev → `com.jarvis.chat.dev.debug`).

Каждый шаг: **действие → ожидание → скрин**. Итог сценария: `PASS` / `FAIL` + где сломалось.

---

## S1 — Cold start (экран грузится)
1. `am start` главной Activity → скрин `s1_1_launch.png`.
2. Ожидание: виден TopAppBar «Jarvis», input-поле, кнопка Send. (пустой чат или восстановленная история)
- **PASS если**: `uiautomator dump` содержит поле ввода + Send; нет краша (PID жив, нет FATAL в logcat).

## S2 — Отправка сообщения
1. Тап по input-полю → `input text "Привет"` → скрин `s2_1_typed.png`.
2. Тап Send → скрин `s2_2_sending.png` (ожидание: user-бабл «Привет» + индикатор загрузки).
3. Ждать ≤15с ответа → скрин `s2_3_reply.png`.
- **PASS если**: появился user-бабл; затем либо assistant-бабл (есть сеть+ключ), либо inline error-строка
  (нет сети/ключа) — **без краша**. Error-хендлинг = валидный результат smoke.

## S3 — Избранное + фильтр
1. Долгий/обычный тап ★ на assistant-бабле → скрин `s3_1_favorited.png` (★ залилась).
2. Тап ★-фильтра в TopAppBar → скрин `s3_2_filtered.png` (в списке только избранные).
3. Тап ★-фильтра ещё раз → скрин `s3_3_all.png` (снова все).
- **PASS если**: после фильтра список короче/равен и содержит избранное; toggle обратимый.

## S4 — Export / Import JSON
1. Тап Export → скрин `s4_1_export.png`; ожидание: снэкбар с путём `chat_history_export.json`.
2. Тап Import (загрузка мока `mock_chat_history.json`) → скрин `s4_2_import.png`.
3. Ожидание: в списке появились сообщения из мока (4 сообщения, 2 избранных).
- **PASS если**: export-снэкбар показан; после import количество сообщений выросло/соответствует моку.

## S5 — Persistence (переживает смерть процесса)
1. Зафиксировать текущее число сообщений (`uiautomator dump`).
2. `am force-stop com.jarvis.chat.dev.debug` → пауза → `am start` снова → скрин `s5_1_relaunch.png`.
3. Ожидание: история та же (сообщения на месте после рестарта процесса).
- **PASS если**: число сообщений после релонча == до force-stop (данные с диска, не in-memory).

---

## Формат отчёта (генерит `run_smoke.sh` → `report.md`)
| Сценарий | Шаги | Результат | Скрины | Где сломалось |
|---|---|---|---|---|
| S1…S5 | n/n | PASS/FAIL | список png | — / диагноз |
Плюс: версия APK, устройство, время, logcat-выжимка FATAL/ERROR при падении.
