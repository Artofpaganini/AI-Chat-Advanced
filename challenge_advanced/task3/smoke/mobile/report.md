# L2 Smoke — Android, через реальный MCP (claude-in-mobile)

**Дата:** 2026-07-23 · **Драйвер:** `claude-in-mobile` MCP v3.14.0 (тулы `device/app/input/ui/screen/system`)
**Устройство:** эмулятор Small_Phone (Android, 720x1280) · **Сборка:** `androidApp-dev-debug.apk`
**Пакет:** `com.jarvis.chat.dev.debug`

> Отличие от прошлого прогона: раньше UI протыкивался напрямую через `adb`. Здесь **весь драйв идёт через MCP-тулы**
> (`app:install/launch/stop`, `input:tap/text`, `ui:tree`, `screen:capture`, `system:wait`). Через `adb` только
> сохранение PNG-артефактов и проверка файла на диске — MCP не умеет писать скриншот в файл.

## Результат: 5/5 PASS

| Сценарий | Вердикт | Скриншоты | Чем доказано |
|---|---|---|---|
| **S1** Cold start | ✅ PASS | `s1_launch.png` | `app:launch` → `screen:capture`: шапка Jarvis, иконки ★/↑/↓, empty-state, поле ввода, Send. Краша нет |
| **S2** Отправка сообщения | ✅ PASS | `s2_typed`, `s2_sending`, `s2_reply` | `input:tap`→`input:text("Privet")`→`input:tap(text:"Send")`. Появился ProgressBar, затем **живой ответ DeepSeek** «Privet! How can I help you today?» + 🔊 TTS |
| **S3** Избранное + фильтр | ✅ PASS | `s3_fav`, `s3_filter`, `s3_all` | Тап ☆→★ на бабле. Фильтр ★: hint `Gone: "Privet"`, `ui:tree` показал только избранный ответ. Повторный тап — «Privet» вернулся (toggle обратим) |
| **S4** Export / Import JSON | ✅ PASS | `s4_export`, `s4_import` | Export → снэкбар с путём; **файл на устройстве проверен**: `files/chat_history_export.json`, 392 B. Import → «Imported history: 6 messages» (2 своих + 4 из мока), мок-баблы отрисованы |
| **S5** Persistence | ✅ PASS | `s5_relaunch.png` | `app:stop` (force-stop) → `app:launch`. Вся история жива: «Privet» + ответ DeepSeek (★ сохранилось) + импортированный мок. Данные не in-memory |

## Здоровье
- `FATAL EXCEPTION` в logcat: **нет**.
- PID после всех сценариев: **жив** (6438).
- Скриншотов: **10** (по шагам).

## Заметки по драйверу
- `input:tap` возвращает **hints** (диффы UI после действия) — часто заменяют скриншот и дешевле в 10 раз.
- Тап по кнопке Send делался **по тексту** (`input:tap text:"Send"`), а не по координатам: клавиатура сдвигает кнопку.
- `system:shell` блокирует пайпы (`|`) как shell-injection — команды с пайпом гонялись через Bash/adb.
- Координаты в `screen:capture` — в пространстве 540x960, MCP сам скейлит на 720x1280 устройства.

## Открытые находки (перенесены из L1, на UI не воспроизводились)
1. `ChatViewModel` не юнит-тестируем без public-ctor у `SendMessageUseCase`.
2. Import MERGE может сбросить локальный favorite (imported перекрывает по id).
