# Скриншоты фичи (task2) — с эмулятора

Демонстрация корректно выполненной задачи task2 (история чата + избранное + export/import JSON),
снято с Android-эмулятора (Small_Phone, dev-debug APK, `com.jarvis.chat.dev.debug`).

| # | Файл | Что показано |
|---|---|---|
| 00 | `00_launch.png` | Cold start — пустой чат, TopAppBar (★ фильтр · ↑ export · ↓ import), input-бар |
| 01a | `01_chat_history.png` | Отправка сообщения → **живой ответ DeepSeek** («Hello! How can I help you today?») + 🔊 |
| 01b | `01_history_imported.png` | **Import JSON** мока → история загружена (4 сообщения, 2 избранных ★) |
| 02 | `02_favorites_filter.png` | **Фильтр избранного** (★) — показаны только избранные сообщения |
| 03 | `03_export_snackbar.png` | **Export JSON** → снэкбар с путём `…/files/chat_history_export.json` |
| 04 | `04_persistence.png` | **Persistence** — после `force-stop` + релонча история и избранное восстановлены (с диска, не in-memory) |

Все возможности фичи подтверждены вживую: чат с DeepSeek, избранное с фильтром, export/import JSON,
переживание смерти процесса.
