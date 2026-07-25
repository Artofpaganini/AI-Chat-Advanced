# feature/chat

Модуль главного экрана чата с AI. Показывает переписку с ассистентом, хранит историю на диске,
даёт избранное, экспорт/импорт, голосовой ввод и озвучку ответов через TTS.

## 1. Что умеет модуль

- **Отправка сообщений** ассистенту и получение ответа (`SendClicked`, `SendMessageUseCase` из `feature/ai`).
- **История чата с персистом** - сообщения сохраняются на диск (Android/iOS) или в `localStorage` (wasmJs)
  и подгружаются при старте экрана.
- **Избранные сообщения** - можно отметить ответ звездой и включить фильтр «только избранное».
- **Таймстампы** - у каждого сообщения есть метка времени `ЧЧ:ММ`.
- **Копирование в буфер** - иконка копирования на сообщении кладёт текст в `ClipboardManager`.
- **Retry на ошибке** - если ответ не пришёл, под последним сообщением появляется ошибка с кнопкой «Retry».
- **Индикатор набора** - пока ждём ответ ассистента, в списке показывается `TypingIndicator`.
- **Очистка истории** - кнопка в топ-баре открывает диалог подтверждения, затем чистит историю.
- **Пустое состояние с подсказками** - на пустом чате показывается приветствие и карточки-подсказки,
  тап по карточке сразу отправляет её текст.
- **Кнопка scroll-to-bottom** - плавающая кнопка появляется, когда список списка проскроллен вверх,
  и мгновенно возвращает к последнему сообщению.
- **TTS-озвучка** - у ответов ассистента (не у сообщений юзера) есть кнопка озвучки через `nl.marc-apps:tts`.
- **Голосовой ввод** - кнопка микрофона запускает распознавание речи (`feature/voice`), текст попадает в поле ввода.
- **Экспорт/импорт истории** - кнопки в топ-баре сохраняют историю в файл и обратно (на данный момент импорт
  в UI тянет мок-файл из ресурсов, `MOCK_HISTORY_PATH`).

## 2. Архитектура

Слои по стандарту проекта:

- `data/` - хранение истории: модели `*DataModel`, `ChatHistoryLocalDataSource` (+ платформенные `actual`),
  мапперы `data ↔ domain`, `ChatHistoryRepositoryImpl`.
- `domain/` - `*Model`, `ChatHistoryRepository` (интерфейс), use-case-ы над ним.
- `presentation/` - `ChatViewModel`, `ChatState`/`ChatUiModel`/`ChatAction`/`ChatEvent`, `ChatUiMapper`, Compose-экран.
- `di/` - `ChatModule.kt`, Koin-граф модуля.

Поток данных строго однонаправленный (UDF):

```
UI -> Action -> ChatViewModel.onAction -> updateState { copy(...) } -> ChatState
   -> ChatUiMapper.map(state) -> ChatUiModel -> UI (recomposition)
```

Одноразовые эффекты (скролл, снекбар) идут не через State, а через `Event`:
`ChatViewModel.postEvent(event)` -> `Channel<ChatEvent>` -> `viewModel.events` -> `LaunchedEffect` в `ChatScreen`
слушает и исполняет (`scrollToBottom()`, `snackbarHostState.showSnackbar(...)`).

`ChatViewModel` наследует `UdfBaseViewModel<ChatAction, ChatUiModel, ChatState, ChatEvent>`
(порядок дженериков: `Action, UiState, State, Event`).

## 3. UDF-контракт

### ChatAction

**Ui** - действия пользователя из Compose-слоя:

| Action | Что делает |
|---|---|
| `InputChanged(text)` | обновляет текст в поле ввода |
| `VoiceTranscribed(text)` | подставляет в поле ввода текст, распознанный голосом |
| `SendClicked` | отправляет текущий текст ввода как сообщение |
| `SuggestionClicked(text)` | подставляет текст подсказки и сразу отправляет его |
| `RetryClicked` | повторяет последний неудавшийся запрос к ассистенту |
| `FavoriteToggled(messageId)` | переключает флаг избранного у сообщения |
| `MessageCopied` | сигнализирует, что текст скопирован (показывает снекбар) |
| `FavoritesFilterToggled` | включает/выключает фильтр «только избранное» |
| `ExportClicked` | экспортирует текущую историю в файл |
| `ImportRequested(json)` | импортирует историю из переданного JSON |
| `ClearHistoryClicked` | открывает диалог подтверждения очистки истории |
| `ClearHistoryConfirmed` | подтверждает очистку истории |
| `ClearHistoryCancelled` | отменяет очистку истории |

**Internal** - реакции на результаты асинхронных операций:

| Action | Что делает |
|---|---|
| `HistoryLoaded(messages)` | подставляет в state историю, загруженную при старте |
| `ReplyReceived(message)` | добавляет в историю ответ ассистента |
| `ReplyFailed` | помечает state ошибкой, снимает индикатор загрузки |
| `Exported(filePath)` | показывает снекбар с путём экспортированного файла |
| `ExportFailed` | показывает снекбар об ошибке экспорта |
| `Imported(messages)` | заменяет историю импортированной, показывает снекбар и скроллит вниз |
| `ImportFailed` | показывает снекбар об ошибке импорта |
| `HistoryCleared` | очищает state после успешной очистки истории |
| `ClearHistoryFailed` | показывает снекбар об ошибке очистки |

### ChatState -> ChatUiModel

| Поле `ChatState` | Поле `ChatUiModel` | Что означает |
|---|---|---|
| `messages` | `messages` | список сообщений (в `UiModel` - уже отфильтрованные по избранному, если фильтр включён) |
| `inputText` | `inputText` | текст в поле ввода |
| `isLoading` | `isLoading` | идёт ожидание ответа ассистента (скрывается под фильтром избранного) |
| `hasError` | `isErrorVisible` | последний запрос завершился ошибкой |
| `isFavoritesFilterActive` | `isFavoritesFilterActive` | включён фильтр «только избранное» |
| `showClearConfirmation` | `showClearConfirmation` | показан диалог подтверждения очистки |
| - | `isSendEnabled` | вычисляется: `inputText` не пустой и нет активной загрузки |
| - | `favoritesCount` | количество избранных сообщений |
| - | `isEmptyState` | чат пуст, не грузится, без ошибки и без фильтра - показать приветствие |
| - | `isFavoritesEmptyState` | фильтр включён, но избранных сообщений нет |

`ChatMessageUiModel` (элемент списка): `id`, `text`, `isFromUser`, `isSpeakable` (озвучиваем только ответы ассистента),
`isFavorite`, `canFavorite` (тоже только у ответов ассистента), `timeLabel`.

### ChatEvent

| Event | Когда отправляется |
|---|---|
| `ScrollToBottom` | после отправки сообщения, получения ответа, загрузки истории или импорта |
| `ShowMessage(text)` | копирование, результат экспорта/импорта/очистки истории - показывает снекбар |

## 4. Use-cases

| Класс | Зачем нужен |
|---|---|
| `LoadChatHistoryUseCase` | читает сохранённую историю при старте экрана |
| `SaveChatHistoryUseCase` | сохраняет текущую историю после каждого изменения (отправка, ответ, избранное) |
| `ClearChatHistoryUseCase` | полностью очищает сохранённую историю |
| `ExportChatHistoryUseCase` | пишет текущую историю в отдельный экспорт-файл, возвращает путь |
| `ImportChatHistoryUseCase` | парсит JSON и мёржит/заменяет текущую историю (`ImportStrategy`) |

## 5. Хранение истории

История лежит в `ChatHistoryDataModel` (`version`, `messages: List<ChatMessageDataModel>`) и пишется/читается
через интерфейс `ChatHistoryLocalDataSource`:

```kotlin
internal interface ChatHistoryLocalDataSource {
    suspend fun readHistory(): ChatHistoryDataModel
    suspend fun writeHistory(history: ChatHistoryDataModel)
    suspend fun writeExport(history: ChatHistoryDataModel): String
    fun parseHistory(rawJson: String): ChatHistoryDataModel
}
```

Фабрика - `expect fun createChatHistoryLocalDataSource(storageConfig, ioDispatcher)` в `commonMain`,
у неё три `actual`-реализации:

- **androidMain / iosMain** - обе используют `ChatHistoryLocalDataSourceImpl` из `commonMain`, который пишет
  файлы через `kotlinx-io` (`SystemFileSystem`) в директорию из `ChatStorageConfigModel.directoryPath`.
- **wasmJsMain** - у браузера нет файловой системы, поэтому там отдельная реализация
  `WebChatHistoryLocalDataSource`, которая хранит историю в `kotlinx.browser.localStorage`
  (ключи `jarvis_chat_history` / `jarvis_chat_history_export`), а не в файлах.

Именно поэтому у wasmJs своя `actual`-реализация, а не переиспользование `ChatHistoryLocalDataSourceImpl` -
файловый API `kotlinx-io` в браузере не работает.

## 6. Точки расширения

- **Новый Action** - добавить `data class`/`data object` в `ChatAction.Ui` или `.Internal`, обработать
  в `when` внутри `ChatViewModel.onAction`, реализовать приватным методом по аналогии с существующими
  (`onXxx()`, апдейт state через `updateState { copy(...) }`, при необходимости `postEvent(...)`).
- **Новое поле в UiModel** - добавить поле в `ChatUiModel`/`ChatMessageUiModel`, посчитать его в
  `ChatUiMapper.map(state)` (или в `toChatMessageUiModel()` для полей на уровне сообщения). Данные,
  необходимые для расчёта, при необходимости сначала завести в `ChatState`.
- **Новый элемент UI** - новый composable-компонент в `presentation/ui/` (по образцу `MessageBubble`,
  `TypingIndicator`), подключить его в `ChatScreen.kt` и прокинуть нужные колбэки в виде `Action`.
- **Новый способ хранения истории** - реализовать `ChatHistoryLocalDataSource` под платформу и подключить
  через `actual fun createChatHistoryLocalDataSource(...)` в соответствующем source set.

## 7. Известные ограничения

- Тесты `ChatHistoryLocalDataSourceImplTest` (8 штук) падают на таргете `wasmJsBrowserTest` с
  `kotlin.UnsupportedOperationException` - это баг окружения (файловые операции `kotlinx-io` не работают
  в headless Chrome), не баг логики модуля. `ChatHistoryLocalDataSourceImpl` рассчитан на файловую систему
  и на wasmJs не используется (см. раздел 5) - тест написан для общей реализации и не учитывает эту специфику target-а.
- Рабочий тест-гейт модуля - `:feature:chat:testAndroidHostTest` (Android host-тесты через `withHostTest {}`
  в `build.gradle.kts`).
- Импорт истории в UI сейчас всегда читает захардкоженный мок-файл `files/mock_chat_history.json` из ресурсов
  (`MOCK_HISTORY_PATH` в `ChatScreen.kt`), а не открывает системный file picker.
