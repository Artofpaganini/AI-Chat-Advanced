# L2 Smoke - Web (wasmJs), через MCP browser-модуль

**Дата:** 2026-07-23 · **Драйвер:** `claude-in-mobile` MCP v3.14.0, модуль `browser` (CDP)
**Таргет:** `http://localhost:8080` - dev-сервер `:composeApp:wasmJsBrowserDevelopmentRun`

## Итог: web-таргет ✅ работает / UI-сценарии ⛔ не прогнаны - упор в драйвер

**Приложение на web рабочее - подтверждено визуально в обычном Chrome:** вкладка `localhost:8080` рисует
шапку «Jarvis», empty-state «Ask Jarvis anything to start the conversation.», поле ввода и кнопку Send.

5 UI-сценариев не прогнаны **не из-за дефекта приложения**, а потому что браузер, который поднимает MCP, -
отдельный инстанс без WebGL. Контраст:

| Браузер | WebGL | `<canvas>` | Рендер на `localhost:8080` |
|---|---|---|---|
| Обычный Chrome пользователя | есть | есть | ✅ работает |
| Инстанс, поднятый MCP (Chrome/150.0.0.0, CDP) | **false** | нет | ⛔ пустая страница (12 DOM-узлов) |

Ниже - что доказано инструментально и чем.

## Доказано (проверки выполнены, с доказательствами)

| Проверка | Результат | Доказательство |
|---|---|---|
| Сервер отдаёт приложение | ✅ | `HTTP 200`, `<title>Jarvis</title>` |
| wasmJs-бандл собирается | ✅ | `wasmJsBrowserDevelopmentExecutableDistribution` -> BUILD SUCCESSFUL |
| Ассеты грузятся в браузере | ✅ | `performance.getEntriesByType('resource')`: `composeApp.js` 570 kB, wasm 3181 kB, wasm(skiko) 5245 kB - все без ошибок |
| Compose-рантайм монтируется | ✅ | `ComposeViewport` создал DOM-контейнеры в `body` |
| **CORS-proxy -> DeepSeek** | ✅ | Браузерный `fetch('/chat/completions')` -> **HTTP 401 «Authentication Fails (governor)»** = ответ **реального** api.deepseek.com сквозь webpack-proxy; `corsBlocked: false`. Плумбинг (proxy + относительный baseUrl) корректен |
| Android-регрессия от web-правок | ✅ | `:androidApp:assembleDevDebug` -> BUILD SUCCESSFUL |

## Блокер: в браузере MCP нет WebGL

```
canvas.getContext('webgl2') -> false
canvas.getContext('webgl')  -> false
```
Проверено в **обеих** сессиях: обычной и `headless:true`. Skiko (рендерер Compose Multiplatform) без WebGL
не создаёт `<canvas>` -> UI не отрисовывается, интерактивных элементов на странице нет
(`document.querySelector('canvas') === null`, всего 12 DOM-узлов - только контейнеры).

**Это ограничение среды, а не приложения:** JS и оба wasm-модуля скачиваются успешно, рантайм стартует,
сетевой слой работает. Не хватает только графического контекста.

Также отмечено: даже при наличии WebGL DOM-селекторы для Compose/wasm бесполезны - весь UI внутри одного
`<canvas>`, поэтому `browser:click(selector|text)` и `snapshot` не применимы; взаимодействие возможно только
координатное (синтетические pointer-события по канвасу).

## Применённое исправление (ждёт рестарта сессии)

MCP-сервер `mobile` перерегистрирован с указанием настоящего Chrome (у него есть GPU/WebGL):

```
claude mcp add --scope user --transport stdio mobile \
  -e CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  -- npx -y claude-in-mobile@latest
```

**Чем закончилось.** Обёртка вернула настоящий GPU, но canvas в этом драйвере так и не появился - значит
поверх GPU есть ещё причина. Web закрыт **Playwright**, он отрисовал приложение с первой попытки. Расширение
`claude-in-chrome` из вариантов выбыло: за несколько рестартов сессии оно так и не подключилось.
Актуальный итог прогона и разбор по инструментам - в `../../FINAL_REPORT.md`.

## Статус сценариев на web

| Сценарий | Статус |
|---|---|
| S1 Cold start | ⛔ не прогнан (нет отрисовки) |
| S2 Отправка сообщения | ⛔ не прогнан на UI; сетевой путь до DeepSeek подтверждён отдельно (см. CORS-proxy) |
| S3 Избранное + фильтр | ⛔ не прогнан |
| S4 Export / Import | ⛔ не прогнан |
| S5 Persistence | ⛔ не прогнан |

**Для сравнения:** те же 5 сценариев на Android через MCP - **5/5 PASS** (`../mobile/report.md`).
