# feature:ai

Модуль отвечает за общение с DeepSeek API: отправка истории сообщений, получение ответа целиком
или потоком, разбор ошибок в доменную модель. Это чистый data/domain-слой без UI и без хранения истории чата.

## 1. Зачем модуль

`feature:ai` делает три вещи:
- собирает HTTP-запрос к DeepSeek (`chat/completions`) из истории сообщений и системного промпта;
- разбирает ответ - целиком (`requestCompletion`) или потоком через SSE (`requestCompletionStream`);
- превращает любые сбои Ktor-клиента в доменную таксономию `AiErrorModel`.

Чего модуль НЕ делает:
- не знает про UI и Compose - здесь нет ни одного `*UiModel` или экрана;
- не хранит историю чата и не решает, что показывать пользователю - это зона `feature:chat`;
- не выбирает модель AI сам - модель приходит снаружи через `DeepSeekModelProvider`.

## 2. Слои

| Каталог | Что внутри |
|---|---|
| `data/model` | `@Serializable internal data class` под запрос/ответ DeepSeek: `ChatCompletionRequestModel`, `ChatMessageRequestModel`, `ChatCompletionResponseModel`, `ChatChoiceResponseModel`, `ChatMessageResponseModel`, `ChatCompletionChunkResponseModel`, `ChatChunkChoiceResponseModel`, `ChatChunkDeltaResponseModel` |
| `data/datasource` | `DeepSeekRemoteDataSource` (интерфейс) + `DeepSeekRemoteDataSourceImpl` - вызовы Ktor; `SseChunkReader.kt` (`parseSseLine`, `sseChunkTextFlow`) и `SseEvent` - чтение потокового ответа построчно |
| `data/mapper` | `AiErrorMapper.kt` (`Throwable.toAiErrorModel()`), `ChatCompletionResponseMapper.kt`, `ChatCompletionChunkResponseMapper.kt`, `ChatMessageRequestMapper.kt` - все top-level extension-функции |
| `data/repository` | `AiRepositoryImpl` - реализация `AiRepository`, единственное место, где `Throwable` превращается в `AiException` |
| `domain/model` | `ChatMessageModel`, `MessageAuthor`, `AiErrorModel`, `AiException`, `DeepSeekConfigModel`, `DeepSeekPromptConfigModel`, `DeepSeekModelIdModel`, `DeepSeekModelProvider` |
| `domain/repository` | `AiRepository` - интерфейс с `sendMessage` и `sendMessageStream` |
| `domain/usecase` | `SendMessageUseCase` (возвращает `Result<ChatMessageModel>`), `SendMessageStreamUseCase` (возвращает `Flow<String>`) |
| `di` | `AiModule.kt` (Koin-модуль `aiModule`), `DeepSeekDefaults.kt` (константы модели и системного промпта) |

## 3. Два пути отправки

`DeepSeekRemoteDataSource` даёт два метода:

```kotlin
suspend fun requestCompletion(messages: List<ChatMessageRequestModel>): ChatCompletionResponseModel

fun requestCompletionStream(messages: List<ChatMessageRequestModel>): Flow<String>
```

`requestCompletion` шлёт `stream = false` и один раз возвращает готовый `ChatCompletionResponseModel`.
`requestCompletionStream` шлёт `stream = true` и открывает соединение через `preparePost` +
`execute { response -> ... }`, читая `response.bodyAsChannel()` построчно, пока сервер шлёт куски ответа.

Оба пути собирают тело запроса одной и той же приватной функцией `buildRequestBody` -
разница только в флаге `stream`. Так системный промпт, история сообщений и текущая модель
никогда не расходятся между обычным и потоковым запросом.

На уровне `domain` этому соответствуют два use-case: `SendMessageUseCase` (оборачивает результат в
`Result<ChatMessageModel>`, гасит все исключения кроме `CancellationException`) и
`SendMessageStreamUseCase` (тонкая обёртка над `AiRepository.sendMessageStream`, ошибки прокидывает наружу как есть).

Кто реально их использует: `feature:chat` (`ChatReplyDelegate`) вызывает только
`SendMessageStreamUseCase` - потоковый ответ печатается в UI по мере прихода токенов.
`SendMessageUseCase` зарегистрирован в DI (`factoryOf(::SendMessageUseCase)`) и покрыт тестами,
но на момент написания README у него нет потребителя за пределами `feature:ai` - это готовый API
для сценария "получить ответ целиком", если он понадобится (например бэкграунд-задача без стриминга в UI).

### Чтение SSE без ktor-client-sse

В version catalog проекта нет зависимости `ktor-client-sse` - её не добавляли. Вместо готовой
библиотеки поток читается вручную в `SseChunkReader.kt`:
- `sseChunkTextFlow(channel, json)` построчно читает `ByteReadChannel` через `channel.readLine()`;
- `parseSseLine(line)` разбирает строку в `SseEvent` - `Data(payload)`, `Done` (маркер `[DONE]`) или `null`,
  если строка не начинается с `data:`;
- на каждый `SseEvent.Data` тело `payload` парсится как `ChatCompletionChunkResponseModel`, из него
  достаётся `delta.content` через `toDeltaTextOrNull()`; битый JSON (`SerializationException`) тихо
  пропускается, поток не падает.

DeepSeek отдаёт SSE в упрощённом виде - только `data:` строки и завершающий `[DONE]`, без `event:`,
`id:` и `retry:`. Полноценный SSE-протокол избыточен для одного этого эндпоинта, поэтому вместо
библиотеки - десяток строк, которые разбирают ровно то, что реально приходит.

## 4. Ошибки

`Throwable.toAiErrorModel()` в `AiErrorMapper.kt` превращает любое исключение Ktor-клиента в `AiErrorModel`:

| Вариант `AiErrorModel` | Когда возникает |
|---|---|
| `Timeout` | `HttpRequestTimeoutException` - истёк один из таймаутов `HttpTimeout` |
| `Unauthorized` | `ClientRequestException` со статусом 401 |
| `RateLimited` | `ClientRequestException` со статусом 429 |
| `BadRequest(message)` | `ClientRequestException` со статусом 400; `message` - тело ответа сервера, либо `exception.message`, если тело пустое |
| `ServerError(code)` | `ServerResponseException` (5xx); `code` - реальный `response.status.value` |
| `NoConnection` | `kotlinx.io.IOException` - нет сети или соединение оборвалось |
| `Unknown` | всё остальное: `ClientRequestException` с другим статусом (например 404) или любой непойманный `Throwable` |

`AiException(error: AiErrorModel)` - единственное исключение, которое видят потребители модуля.
Маппинг происходит в `AiRepositoryImpl`: `requestCompletion`/`requestCompletionStream` оборачиваются
в `try/catch`, `CancellationException` пробрасывается как есть, всё остальное превращается в `AiException`.
Ktor-типы (`ClientRequestException`, `ServerResponseException`, `HttpRequestTimeoutException`) наружу из
`data`-слоя не выходят - `domain` и всё, что снаружи модуля, видит только `AiErrorModel`.

Ключевая роль `expectSuccess = true` (выставлен в `AiModule.kt` при создании `HttpClient`): без него
Ktor не бросает исключение на HTTP-коды 4xx/5xx, тело просто вернётся с кодом ошибки внутри, и код в
`data/mapper` его не поймает. С `expectSuccess = true` любой не-2xx код долетает как `ClientRequestException`
или `ServerResponseException`, и его можно разобрать в `toAiErrorModel()`.

## 5. Конфигурация

| Параметр | Тип/модель | Источник |
|---|---|---|
| API-ключ и base URL | `DeepSeekConfigModel(apiKey, baseUrl)` | собирается в `composeApp/di/KoinInitializer.kt` из `AppConfig.deepSeekApiKey` / `AppConfig.deepSeekBaseUrl` (Android - `BuildConfig.DEEPSEEK_API_KEY` из `local.properties`, iOS/wasm - свои конфиги платформы) |
| Модель | `DeepSeekModelProvider.currentModel(): String` | тоже собирается в `KoinInitializer.kt`, читает `ObserveAiModelUseCase` из `feature:settings` |
| Системный промпт | `DeepSeekPromptConfigModel(systemPrompt)` | собирается прямо в `AiModule.kt` из `DeepSeekDefaults.SYSTEM_PROMPT` |

`DeepSeekConfigModel` и `DeepSeekModelProvider` сам `feature:ai` не регистрирует - оба типа объявлены в
`domain/model`, но их конкретные Koin-биндинги живут в `composeApp`, потому что модель зависит от
пользовательской настройки (`feature:settings`), а не от чего-то внутреннего для `feature:ai`.

Модель передаётся не значением, а через `fun interface DeepSeekModelProvider { fun currentModel(): String }`.
`DeepSeekRemoteDataSourceImpl.buildRequestBody` вызывает `modelProvider.currentModel()` на каждый запрос,
а не один раз при сборке графа Koin. Это подтверждено тестом
`requestCompletion_readsModelFromProviderOnEveryCall` - если пользователь переключил модель в настройках
между двумя сообщениями, второй запрос уйдёт уже с новой моделью без пересборки DI-графа.

Таймауты (`AiModule.kt`, `HttpTimeout`):

| Таймаут | Значение | Комментарий |
|---|---|---|
| `requestTimeoutMillis` | 90 000 мс | общий таймаут запроса |
| `connectTimeoutMillis` | 10 000 мс | установка соединения |
| `socketTimeoutMillis` | 60 000 мс | базовый - для обычного `requestCompletion` |

Для потокового запроса `socketTimeoutMillis` переопределяется прямо в `requestCompletionStream` через
`timeout { socketTimeoutMillis = STREAM_SOCKET_TIMEOUT_INFINITE_MILLIS }` (`Long.MAX_VALUE`). SSE-соединение
держится открытым, пока сервер шлёт токены - между двумя чанками может пройти больше 60 секунд, и это не
обрыв связи, а нормальная генерация ответа. Общий `requestTimeoutMillis` при этом не снимается.

## 6. Как добавить нового провайдера AI

Если понадобится, например, другой сервис вместо DeepSeek, точки расширения такие:
1. `data/model` - новые `*RequestModel`/`*ResponseModel` под формат нового API (текущие модели названы
   с префиксом `ChatXxx`, а не `DeepSeekXxx`, поэтому их можно переиспользовать один в один, если формат
   совместим с OpenAI-style chat completions).
2. `data/datasource` - новая реализация `DeepSeekRemoteDataSource` (либо переименовать интерфейс в
   провайдеронезависимый, если провайдеров станет больше одного) со своим URL и, при необходимости, своим
   разбором стрима вместо `SseChunkReader`.
3. `domain/model` - свой `*ConfigModel` вместо `DeepSeekConfigModel`, если нужны другие поля конфигурации.
4. `di/AiModule.kt` - переключить биндинг `DeepSeekRemoteDataSource::class` на новую реализацию.

Переиспользуется без изменений: `AiRepository`/`AiRepositoryImpl` (не знают про DeepSeek, только про
интерфейс дата-сорса), оба use-case, вся таксономия `AiErrorModel` и маппер `Throwable.toAiErrorModel()`
(он завязан на типы исключений Ktor-клиента, а не на конкретного провайдера).

## 7. Тесты

Тестами покрыты все слои модуля:
- `data/datasource/DeepSeekRemoteDataSourceImplTest` - путь запроса, системный промпт перед историей,
  флаг `stream`, модель из провайдера на каждый вызов, разбор SSE-чанков, проброс `ClientRequestException`
  для обоих методов отправки;
- `data/datasource/SseChunkReaderTest` - `parseSseLine` и `sseChunkTextFlow`: обычные чанки, `[DONE]`,
  битый JSON, пустой/`null` `delta.content`;
- `data/mapper/AiDataMappersTest` - `toChatMessageModel`, `toChatMessageRequestModel`, `toDeltaTextOrNull`;
- `data/mapper/AiErrorMapperTest` - все варианты `AiErrorModel` из таблицы в разделе 4;
- `data/repository/AiRepositoryImplTest` - `sendMessage`/`sendMessageStream`, порядок истории, маппинг
  ошибок в `AiException`, проброс `CancellationException` без оборачивания;
- `domain/usecase/SendMessageUseCaseTest`, `SendMessageStreamUseCaseTest` - успех/ошибка/отмена на уровне use-case.

Гейт модуля - `./gradlew :feature:ai:testAndroidHostTest`. Гонять строго с `--rerun --no-build-cache`:

```bash
./gradlew :feature:ai:testAndroidHostTest --rerun --no-build-cache
```

Build cache в этом проекте уже отдавал ложно-зелёный результат - таск рапортовал успех, хотя тесты
фактически не запускались. Без `--rerun --no-build-cache` зелёный гейт ничего не гарантирует.
