# Restart-промпт (вставить первым сообщением после рестарта)

---

Продолжаем task3 в `/Users/Victor/AI-Chat-Advanced`, ветка `task3`. Приложение - Jarvis (KMM + Compose
Multiplatform, чат с DeepSeek). Делаем **полный L2-чек с нуля по моим сценариям**, оба таргета.

Подними готовность и доложи, потом жди мои сценарии:

1. Эмулятор `Small_Phone` (`~/Library/Android/sdk/emulator/emulator -avd Small_Phone -no-snapshot-save`),
   дождись `sys.boot_completed`.
2. Поставь APK через MCP: `app:install` ->
   `/Users/Victor/AI-Chat-Advanced/androidApp/build/outputs/apk/dev/debug/androidApp-dev-debug.apk`
   (пакет `com.jarvis.chat.dev.debug`). Пересобирать не надо, если APK свежий.
3. Web dev-сервер: `export JAVA_HOME=/Users/Victor/Library/Java/JavaVirtualMachines/corretto-21.0.9/Contents/Home`,
   затем `./gradlew :composeApp:wasmJsBrowserDevelopmentRun` (слушает `localhost:8080`, в нём CORS-proxy на DeepSeek).
4. **Проверь, починился ли WebGL**: `device(enable_module:'browser')` -> `browser:open localhost:8080` ->
   `evaluate`: есть ли `canvas` и `getContext('webgl2')`. Должен подняться настоящий Chrome (в конфиг MCP
   прописан `CHROME_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`).
   Если WebGL так и `false` - скажи сразу, дальше web гоним через расширение `claude-in-chrome`.
5. Доложи готовность: Android ✅/❌, Web ✅/❌ - и жди сценарии.

Формат сценариев и словарь действий - `challenge_advanced/task3/smoke/SCENARIOS_CATALOG.md`.

## Верифицированный стейт (не переделывать)
- **claude-in-mobile МСР починен**: user-scope, `npx -y claude-in-mobile@latest` (без `@latest` npx брал brew
  Rust-CLI из PATH -> 0 тулов) + `env.CHROME_PATH` на настоящий Chrome.
- **Android L2 через MCP: 5/5 PASS** (`smoke/mobile/report.md`, 10 скринов) - живой ответ DeepSeek,
  export-файл 392 B на устройстве, persistence после force-stop.
- **L1 код-тесты: 30 тестов, зелёные** (`:feature:chat:testAndroidHostTest :feature:ai:testAndroidHostTest`).
- **Web-таргет wasmJs рабочий**: собирается, отдаётся, js+оба wasm грузятся, Compose монтируется,
  CORS-proxy до реального DeepSeek подтверждён (401 от api.deepseek.com, без CORS-блока).
  В обычном Chrome рисуется нормально. Не прогнаны только UI-сценарии - упор был в браузер MCP без WebGL.

## Ограничения (жёсткие)
- Ключ DeepSeek - только `local.properties` (gitignored) и generated-файл в `build/`. **Не хардкодить, не коммитить.**
- НЕ трогать и НЕ коммитить `/Users/Victor/work`.
- Коммит/пуш - только по явной просьбе. В дереве ~30 незакоммиченных изменений (web-таргет + доки task3).
- Smoke: ставить APK **поверх** (`-r`), без `pm clear`/uninstall.
