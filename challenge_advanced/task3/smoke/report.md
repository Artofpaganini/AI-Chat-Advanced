# Smoke-отчёт (L2) - AI-Chat-Advanced

- **Устройство:** Android emulator `Small_Phone` (sdk_gphone16k_arm64, 720×1280, dens 320)
- **APK:** `androidApp-dev-debug.apk` (`com.jarvis.chat.dev.debug`)
- **Дата:** 2026-07-22 · **Драйвер:** adb (реальные тапы + `screencap`) · **FATAL за прогон:** 0

| Сценарий | Результат | Скрины | Проверено |
|---|---|---|---|
| **S1** Cold start | ✅ PASS | `s1_launch.png` | экран рендерится (Jarvis, input, Send, empty-state), нет краша |
| **S2** Отправка сообщения | ✅ PASS | `s2_typed`, `s2_sending`, `s2_reply` | user «Privet» -> **реальный ответ DeepSeek** «Privet! How can I help you today?» + 🔊 |
| **S3** Избранное + фильтр | ✅ PASS | `s3_fav`, `s3_filter`, `s3_all` | ☆->★ на бабле; фильтр ★ показал только избранное (user скрыт); toggle обратим |
| **S4** Export / Import JSON | ✅ PASS | `s4_export`, `s4_import` | снэкбар «History exported to …/chat_history_export.json»; файл на диске (391B); import мока -> сообщения появились |
| **S5** Persistence | ✅ PASS | `s5_relaunch.png` | `force-stop` убил процесс -> релонч -> вся история жива (Privet+ответ+мок), не in-memory |

**Вердикт L2: 5/5 PASS.** Приложение стабильно, критичный флоу (чат->ответ->избранное->export/import->persistence) работает вживую.

## Диагностика (что смотреть при падении)
- Краш: `adb logcat -d | grep "FATAL EXCEPTION"` + скрин шага.
- Нет ответа DeepSeek: `adb logcat | grep -iE "ktor|deepseek|401|403|UnknownHost"` (ключ/сеть).
- Инсеты/смещение кнопки при клавиатуре: Send уезжает вверх (imePadding) - тап по актуальным координатам.

## Перепрогон
```bash
./challenge_advanced/task3/smoke/run_smoke.sh   # авто-раннер (install->launch->сценарии->shots->report)
```
Скрины: `shots/`.
