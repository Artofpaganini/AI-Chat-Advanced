# Финальный отчёт о тестировании - task3

| Поле | Значение |
|---|---|
| Дата | 2026-07-23 |
| Приложение | AI-Chat-Advanced (Jarvis) - KMM + Compose Multiplatform, чат с DeepSeek |
| Ветка | `task3` |
| Android | эмулятор `Small_Phone`, драйвер claude-in-mobile (MCP) |
| Web | dev-сервер `localhost:8080`, драйвер Playwright (MCP) |
| Бэкенд | живой DeepSeek, реальные ответы, не моки |

---

## Итог

**Оба уровня зелёные: 78/78 код-тестов и 8/8 UI-прогонов. Вердикт - MERGE-READY.**

| Требование задачи (PLAN.md) | Статус | Чем закрыто |
|---|---|---|
| L1: код-тесты на 3+ модуля | ✅ | 3 модуля - `feature/chat`, `feature/ai`, `core/viewmodel` |
| L1: минимум 3 файла тестов | ✅ | 11 файлов, из них 6 новых в этом прогоне |
| L1: зелёные с первого запуска | ✅ | `BUILD SUCCESSFUL in 28s`, 0 failed |
| L1: отчёт с файлами, числом тестов, выводом, находками | ✅ | секция «Уровень 1» + секция «Находки» |
| L2: 3-5 пользовательских сценариев | ✅ | 4 сценария, прогнаны на двух таргетах |
| L2: агент сам протыкивает UI через MCP, не заглушки | ✅ | claude-in-mobile (android) + Playwright (web) |
| L2: скриншот на каждом шаге | ✅ | 24 скриншота (11 android + 13 web) |
| L2: PASS/FAIL и диагноз при провале | ✅ | 8/8 PASS, диагнозы в секции «Находки» |
| Интеграция в flow (`pr-check` + «задеплоил фичу -> прогони заново») | ✅ | `pr-check.md` + этот отчёт как результат прогона |

---

## Уровень 1 - код-тесты

Команда: `./gradlew :feature:chat:testAndroidHostTest :feature:ai:testAndroidHostTest :core:viewmodel:testAndroidHostTest`
Результат: `BUILD SUCCESSFUL in 28s`, **78 тестов, 0 падений, зелёные с первого прогона**.
Было 30 тестов -> стало 78. Добавлено 6 файлов и 48 тестов.

| Модуль | Класс тестов | Тестов | Новый |
|---|---|---|---|
| `core/viewmodel` | `UdfBaseViewModelTest` | 7 | 🆕 |
| `feature/ai` | `AiDataMappersTest` | 7 | 🆕 |
| `feature/ai` | `AiRepositoryImplTest` | 5 | 🆕 |
| `feature/ai` | `DeepSeekRemoteDataSourceImplTest` | 7 | 🆕 |
| `feature/ai` | `SendMessageUseCaseTest` | 2 | - |
| `feature/chat` | `ChatViewModelTest` | 14 | 🆕 |
| `feature/chat` | `ChatHistoryLocalDataSourceImplTest` | 8 | 🆕 |
| `feature/chat` | `ChatDataMappersTest` | 7 | - |
| `feature/chat` | `ChatHistoryRepositoryImplTest` | 7 | - |
| `feature/chat` | `ChatHistoryUseCasesTest` | 7 | - |
| `feature/chat` | `ChatUiMapperTest` | 7 | - |

Правки, без которых тесты было не написать:

| Что поправлено | Зачем |
|---|---|
| `ktor-client-mock` в version catalog | нужен MockEngine для тестов датасорса |
| `AiRepository` -> public, у `SendMessageUseCase` снят `internal` с конструктора | иначе `ChatViewModel` не собрать из чужого модуля. Раньше это было зафиксировано как находка о тестируемости, теперь закрыто |
| в `core/viewmodel` включён `withHostTest {}` + тестовые зависимости | у модуля вообще не было тестового source set |

---

## Уровень 2 - UI smoke через MCP

4 сценария x 2 таргета = **8 прогонов, 8 PASS**. FATAL за весь прогон - 0.
Проверка избранного и фильтра ★ встроена в сценарии 2 и 5, отдельным прогоном не считается.

| Сценарий | Android | Web | Чем доказано |
|---|---|---|---|
| 1 - установка и отображение | ✅ PASS | ✅ PASS | android: `app:install` -> Success, `app:launch` -> MainActivity, `ui:assert_visible("Ask Jarvis anything to start the conversation.")` -> PASS, PID живой, FATAL 0. web: `browser_navigate` -> Page Title `Jarvis`, на скрине шапка, empty-state, поле ввода, Send |
| 2 - отправка сообщения | ✅ PASS | ✅ PASS | текст введён ровно как дал пользователь - `Privet che kak? ` с концевым пробелом, приложение пробел обрезает (`inputText.trim()` в `ChatViewModel.onSendClicked()`) - штатное поведение, не дефект. Живые ответы DeepSeek, **разные на двух таргетах**: android `Privet! Vse normalno, rabotayu. Chem mogu pomoch?`, web `Privet! Vse ochen' horosho, spasibo. Chem mogu pomoch?` - это два независимых вызова, а не повтор записи. Вопрос про Эверест: web кириллицей `Что такое Эверест?` -> ответ по-русски (8848 м, Гималаи, граница Непала и Китая), android латиницей `Chto takoe Everest?` -> `8 848.86 metrov`, `assert_visible("8 848.86")` -> PASS. Избранное: android ☆ -> ★ видно визуально, web подтверждено функционально через фильтр |
| 4 - Export / Import | ✅ PASS | ✅ PASS | android: снэкбар `History exported to /data/user/0/com.jarvis.chat.dev.debug/files/chat_history_export.json`, файл проверен на устройстве - **988 байт**, внутри валидный JSON с реальными сообщениями. web: снэкбар `History exported to jarvis_chat_history_export`, ключ localStorage **1010 байт**. Import на обоих: `Imported history: 8 messages.` (4 своих + 4 из мока), `assert_visible("Batch similar tasks together")` -> PASS |
| 5 - Persistence | ✅ PASS | ✅ PASS | android: `app:stop`, затем `pidof` **пуст** - процесс убит по-настоящему, после `app:launch` новый PID 9127 (был 4889), с диска прочитано **8 сообщений, 3 избранных**. web: hard-reload, из localStorage **8 сообщений, 3 избранных**. Фильтр избранного на обоих оставил ровно 3, `assert_gone("Privet che kak?")` -> PASS |

---

## Находки

### Дефекты приложения

| # | Находка | Где видно | Диагноз и лечение |
|---|---|---|---|
| 1 | Иконки не рисуются на web - вместо ★, ⬆, ⬇, 🔊 квадратики-тофу, и в шапке, и на баблах. Логика цела: тап проходит, фильтр работает | `web/shots/s1_web_launched.png`, `web/shots/s2_06_favorited.png` | в wasmJs-сборке нет шрифта с этими глифами, а у Skiko нет системного фолбэка как у Android. Лечится подключением шрифта в `composeResources` либо заменой символьных иконок на векторные |
| 2 | Снэкбар на web вводит в заблуждение - пишет «exported to jarvis_chat_history_export», как будто это путь к файлу | `web/shots/s4_01_export.png` | это ключ localStorage, а не файл. Поправить текст снэкбара для web-таргета |

### Ограничения инструментов, не дефекты приложения

| # | Находка | Диагноз и обход |
|---|---|---|
| 3 | Кириллица не вводится на android | `adb input text` не умеет не-ASCII, падает `NullPointerException at InputShellCommand.sendText`, задать буфер обмена драйвер не умеет. Обход - ставить ADBKeyboard. В прогоне обошлись латиницей |
| 4 | Web-драйверу нужен настоящий GPU | Skiko запрашивает WebGL с `failIfMajorPerformanceCaveat: true`. Под софтверным рендерингом контекст возвращается null **молча**, без исключения, и приложение просто не рисуется |
| 5 | canvas Compose лежит в shadow DOM | `document.querySelector('canvas')` его не находит. Проверять надо обходом shadow-root либо скриншотом |

### Уточнение старой находки

| # | Было | Стало |
|---|---|---|
| 6 | «Импорт MERGE сбрасывает favorite» | Сбрасывает **только при совпадении `id`**. В этом прогоне id были разные, локальное избранное на сообщении про Эверест выжило после импорта |

---

## Артефакты

| Что | Где | Сколько |
|---|---|---|
| Скриншоты android | `challenge_advanced/task3/smoke/user-run/mobile/shots/` | 11 |
| Скриншоты web | `challenge_advanced/task3/smoke/user-run/web/shots/` | 13 |
| Промпты L1 и L2 | `challenge_advanced/task3/prompts.md` | - |
| План и критерии приёмки | `challenge_advanced/task3/PLAN.md` | - |
| Профиль флоу и его отчёт | `challenge_advanced/task3/pr-check.md`, `pr-check-report.md` | - |

Android: `s1_01_installed.png`, `s1_02_launched.png`, `s1_android_launched.png`, `s2_01_typed.png`,
`s2_02_reply1.png`, `s2_03_reply2_everest.png`, `s2_04_favorited.png`, `s4_01_export.png`,
`s4_02_import.png`, `s5_01_relaunch.png`, `s5_02_filter_favorites.png`.

Web: `s1_web_launched.png`, `s2_01_typed.png`, `s2_02_sending.png`, `s2_03_reply1.png`,
`s2_04_typed_cyrillic.png`, `s2_05_reply2_everest.png`, `s2_06_favorited.png`, `s2_07_filter_check.png`,
`s2_08_filter_off.png`, `s4_01_export.png`, `s4_02_import.png`, `s5_01_reload.png`,
`s5_02_filter_favorites.png`.

---

## Вердикт

**MERGE-READY.**

Уровень 1 зелёный - 78/78 с первого прогона. Уровень 2 зелёный - 8/8 PASS на двух таргетах, 0 FATAL,
единственная ошибка в консоли web за весь прогон - `favicon.ico 404`. Два дефекта приложения найдены на
web, оба косметические и не ломают логику: тап по звезде проходит, фильтр работает, данные переживают
рестарт процесса. Три пункта из находок - ограничения тестовых инструментов, к коду приложения отношения
не имеют. Все требования задачи закрыты.
