# Restart-промпт (вставить первым сообщением после рестарта)

---

Продолжаем task3 в `/Users/Victor/AI-Chat-Advanced`, ветка `task3`. Приложение - Jarvis (KMM + Compose
Multiplatform, чат с DeepSeek). Идём по `challenge_advanced/task3/PLAN.md`, сценарии даёт пользователь
по одному, каждый закрывается его апрувом.

Подними окружение и доложи готовность:

1. Эмулятор `Small_Phone` (`~/Library/Android/sdk/emulator/emulator -avd Small_Phone -no-snapshot-save`),
   дождись `sys.boot_completed`.
2. Web dev-сервер: `export JAVA_HOME=/Users/Victor/Library/Java/JavaVirtualMachines/corretto-21.0.9/Contents/Home`,
   затем `./gradlew :composeApp:wasmJsBrowserDevelopmentRun` (слушает `localhost:8080`, внутри CORS-proxy на DeepSeek).
3. **Проверь, что WebGL наконец есть:** `device(enable_module:'browser')` -> `browser:open localhost:8080` ->
   `evaluate`: `getContext('webgl2')` и наличие `canvas`. Ожидание - **true и canvas отрисован**.
4. Доложи: Android ✅/❌, Web ✅/❌, и жди сценарий от пользователя.

## Уже сделано, переделывать не надо

- **Уровень 1 закрыт:** 78 тестов, 0 падений, зелёные с первого прогона. 6 новых файлов (48 новых тестов).
  Команда: `./gradlew :feature:chat:testAndroidHostTest :feature:ai:testAndroidHostTest :core:viewmodel:testAndroidHostTest`.
- **Сценарий 1, Android: PASS.** `app:install` -> Success, `app:launch` -> старт,
  `ui:assert_visible("Ask Jarvis anything to start the conversation.")` -> PASS, PID живой, FATAL = 0.
  Скрины: `smoke/user-run/mobile/shots/s1_01_installed.png`, `s1_02_launched.png`.
- **Сценарий 1, Web: не закрыт** - ждал этого рестарта.

## Починка web-драйвера (главное, ради чего рестарт)

Причина была не в приложении. Модуль `browser` пакета `claude-in-mobile` (`src/browser/client.ts`) жёстко
зашивает `--disable-gpu` при запуске Chrome через `chrome-launcher`, а в текущем Chrome этот флаг убивает и
программный WebGL. Skiko без WebGL не создаёт `DirectContext.makeGL()` -> Compose не рисует.

Проверено фактом: `--disable-gpu` -> WebGL NO; `--disable-gpu --enable-unsafe-swiftshader` -> WebGL YES.

Решение без форка пакета: `CHROME_PATH` в конфиге MCP указывает на обёртку
`~/.claude/bin/chrome-swiftshader`, которая дописывает `--enable-unsafe-swiftshader` и пробрасывает остальные
аргументы. Обновления `claude-in-mobile@latest` её не затирают.

## Ограничения (жёсткие)
- Ключ DeepSeek - только `local.properties` (gitignored) и generated-файл в `build/`. Не хардкодить, не коммитить.
- НЕ трогать и НЕ коммитить `/Users/Victor/work`.
- Коммит/пуш - только по явной просьбе.
- Smoke: APK ставить **поверх** (`-r`), без `pm clear`/uninstall.
- Каждый шаг размечать: `▶️ ШАГ`, `🎯 Задача`, `✅ Итог` / `❌ Провал`.
