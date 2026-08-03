# Разведка: JarvisChat + challenge_advanced task6..task9

Профиль: `research` (base) · размер L · консилиум 4 линз (by-container / by-entity / by-content / by-callers)
Дата: 2026-07-31 · HEAD: `7ae0185` (ветка `task9`, дерево чистое)

---

## 1. Основной проект - JarvisChat

KMP + Compose Multiplatform чат с AI-ассистентом. Таргеты: Android, iOS, wasmJs.

### Модули (`settings.gradle.kts:40-46`)

| Модуль | Назначение |
|---|---|
| `:androidApp` | Точка входа Android (Application + Activity) |
| `:composeApp` | KMP-обвязка: entry points Android/iOS/wasmJs, DI init, тема, `App()` |
| `:core:viewmodel` | UDF-база: `UdfBaseViewModel`, `UiMapper` |
| `:feature:ai` | Клиент DeepSeek/локальных моделей, SSE-стрим, use-cases отправки |
| `:feature:chat` | Экран чата, история, сессии, экспорт/импорт, речь |
| `:feature:settings` | Настройки: AI-модель, AI-провайдер, тема |
| `:feature:voice` | STT через `expect/actual`, без Koin-модуля |

### Стек (`gradle/libs.versions.toml`)

Kotlin 2.4.0 · CMP 1.11.1 · Material3 1.10.0-alpha05 · AGP 9.2.1 · Ktor 3.5.1 ·
kotlinx.serialization 1.11.0 · coroutines 1.11.0 · Koin 4.2.2 · DataStore 1.2.1 ·
TTS `nl.marc-apps:tts` 3.0.0 · Napier 2.7.1 · Turbine 1.2.1 · detekt 1.23.8 · ktlint 1.8.0
minSdk 30 / targetSdk 37 / compileSdk 37 · iOS min 15.0

### Ядро UDF

`core/viewmodel/src/commonMain/kotlin/com/jarvis/chat/core/viewmodel/UdfBaseViewModel.kt:16`
```
abstract class UdfBaseViewModel<Action, UiState, State, Event>(initialState, uiMapper)
```
- `:28` `uiState: StateFlow<UiState>` через `map{}.stateIn(...)`
- `:40` `protected fun updateState(reducer: State.() -> State)` -> `stateFlow.update(...)` - атомарно, `.value =` нигде
- `:36,44` one-off события через `Channel` + `postEvent`
- `UiMapper.kt:3` - `interface UiMapper<in State, out UiModel>`

### DI

Единая точка - `composeApp/src/commonMain/kotlin/com/jarvis/chat/di/KoinInitializer.kt:21`, гард от повторного старта `:22`.
Подключает `chatModule(...)` `:73` и `settingsModule` `:74`; `aiModule` тянется транзитивно через `includes(aiModule)` в `ChatModule.kt:35`.

### Ключевые точки входа

- `androidApp/.../JarvisApplication.kt:9` - собирает `AppConfig` из `BuildConfig` (`DEEPSEEK_API_KEY`, `LOCAL_MODEL_BASE_URL`), `:17` -> `initKoin(appConfig)`
- `androidApp/.../MainActivity.kt:9` - `setContent { App() }`
- `composeApp/src/iosMain/.../MainViewController.kt:13` - iOS-вход; **`:16` `deepSeekApiKey = ""`** - ключ на iOS не прокинут
- `androidApp/build.gradle.kts:14,30` - ключ из `local.properties` -> `BuildConfig`, не хардкод (правило соблюдено)
- Один flavor `dev` (`:34-42`), buildTypes debug/release, minify off в обоих (`:55-65`)

### Три AI-провайдера

`feature/ai/.../domain/model/AiProviderTypeModel.kt`: `CLOUD_DEEP_SEEK` / `LOCAL_MLX` / `LOCAL_TRIAGE`.
Это прямой след challenge-задач: локальные дообученные модели из task6/task7 подключены в само приложение.

---

## 2. Git-топология

Линейная цепь, каждая ветка - прямой потомок предыдущей:

```
main (d9a1293) == feature/chat-history
  -> ... -> task5 (0950f91) -> task6 (f79c7cb) -> task7 (a207c5d) -> task8 (b9c6c8a) -> task9 (7ae0185, HEAD)
```

`task9` в `main` НЕ влит.

| Переход | Файлов | Строк | Что |
|---|---|---|---|
| task6..task7 | 82 | +19666/-0 | только новое: `task1..6/RESULT.md` + весь `task7/*`; кода приложения не тронуто |
| task7..task8 | 87 (51A/36M) | +8895/-37 | `task8/*` + правки `feature/ai`, `feature/chat`, `feature/settings`, `AppConfig`, `KoinInitializer` |
| task8..task9 | 67 (40A/27M) | +5671/-190 | `task9/*` + слой ChatSession* в `feature/chat` (multi-session чат) |
| main..task9 | 735 | +90106/-362 | весь путь task2..task9 |

### Расхождение с origin

- task6, task7, task9 - синхронны с origin
- **task8: локальная ветка опережает `origin/task8` на 1 коммит** - `b9c6c8a fix(task7): vote by majority within equal severity, and know all six routes` не запушен

---

## 3. challenge_advanced - задачи 6..9

Общий домен всех четырёх: ассистент **ALVA** - коуч для родителей детей 0-3 лет.
Общие данные: `task7/data/cases.jsonl` - 50 кейсов (20 clean / 15 borderline / 15 noisy), их переиспользуют task8 и task9.

### task6 - дообучение генерации (fine-tuning)

Постановка (`task6/PLAN.md:10-25`): научить модель отвечать «в стиле компании» - жёсткая структура ответа
(вводная <=100 слов, 3-5 пунктов по <=25 слов, без диагнозов/дозировок, красные флаги -> скорая).

Сделано:
- Датасет 94 примера (train 74 / eval 20), 45.74% реальных данных, 9 бакетов, послойный сплит seed 1337, 0 ошибок валидатора
- Харнесс: `build_dataset.py`, `validate_jsonl.py`, `score.py` (13 правил), `to_mlx.py`, `finetune_client.py` (dry-run по умолчанию), `memorization_check.py`, `smoke_report.py`
- Клиент файнтюна достучался до OpenAI: авторизация ок, файлы загружены (200), **джоба отклонена 403 - «OpenAI is winding down the fine-tuning platform» с 7 мая 2026**
- Сверх задания: локальная Q-LoRA на `drammich/T-pro-it-2.1-4bit` (32.8B, 4-бит), rank16, 250 итераций, 1ч40м на MacBook M4 Pro, стоимость 0
- Сверх задания: интеграция в приложение вторым AI-провайдером, переключение DeepSeek/Local без перезапуска

Результаты:

| Метрика | База T-pro | + LoRA (ckpt 25) |
|---|---|---|
| Средний score | 0.4174 | **0.9163** |
| Красные флаги | 0/6 | **6/6** |

- `gpt-4o-mini` тоже даёт 0/6 по красным флагам
- Зубрёжки нет: `memorized: 0` на обоих проверенных чекпоинтах
- Val loss минимум на итерации 25, дальше рост - чекпоинт выбран прямым замером поведения, не по loss
- Смоук 30 вопросов: **«НЕ ГОТОВО»** - 3/3 экстренных пойманы, но 2 ложные тревоги из 27 неэкстренных
- `mlx_lm.fuse` на 4-битной базе ломает дообучение: 1/3 маркеров шаблона вместо 3/3
- Честные ограничения: train всего 59 примеров (рекомендуется >=100), медицинской вычитки нет, один автор train+eval

#### Что реально принёс коммит `f79c7cb` («task 6»)

124 файла, +14282/-77, автор ViktarDabrou, 2026-07-28. Не squash-маркер - два несвязанных блока в одном коммите.

**Блок 1 - эксперимент** `challenge_advanced/task6/` целиком (~60 файлов, 100% add).

**Блок 2 - рабочая фича «выбор AI-провайдера»** в самом приложении:
- `androidApp/build.gradle.kts` - новый `LOCAL_MODEL_BASE_URL` в `BuildConfig`, дефолт `http://10.0.2.2:8080/`, значение из `local.properties`
- `androidApp/src/debug/AndroidManifest.xml` + `res/xml/network_security_config.xml` (оба новые) - cleartext разрешён на `127.0.0.1` / `10.0.2.2` / `localhost`, debug-флейвор, чтобы эмулятор достучался до локального MLX-сервера
- `feature/ai/.../AiProviderTypeModel.kt` (новый enum), `AiProviderConfigModel.kt` (baseUrl / modelId / systemPrompt / isApiKeyRequired / adapterPath / maxTokens / temperature / repetitionPenalty), `AiProviderConfigProvider.kt` (функциональный интерфейс)
- `feature/ai/.../di/DeepSeekDefaults.kt` - **снят `internal`**, добавлены `LOCAL_MODEL_ID`, `LOCAL_BASE_URL`, **`LOCAL_MODEL_ADAPTER_PATH` с хардкодом `/Users/Victor/models/alva-tpro-lora-ckpt25`**, `LOCAL_MAX_TOKENS=900`, `LOCAL_TEMPERATURE=0.6`, `LOCAL_REPETITION_PENALTY=1.1`, `LOCAL_SYSTEM_PROMPT` (текст про приложение **ALVA** и baby-care, не про Jarvis-чат)
- `feature/settings/*` - целая вертикаль `AiProviderModel` (`DEEP_SEEK_CLOUD` / `LOCAL_MLX`): datasource, repository, `ObserveAiProviderUseCase`, `SaveAiProviderUseCase`, `AiProviderMapper`, `AiProviderUiModel`, переключатель в `SettingsBottomSheet.kt`
- `composeApp/.../KoinInitializer.kt` переписан: вместо статичного `DeepSeekConfigModel` теперь `AiProviderConfigProvider` выбирает конфиг по текущему `AiProviderModel`
- побочно вынесены `ChatStreamChunkDataModel.kt` / `ChatStreamChunkDataModelMapper.kt` (модели стриминга)

Замечания к блоку 2 (требуют проверки на текущем HEAD, см. раздел 7):
1. абсолютный путь машины разработчика в общей константе - у другого разработчика и на CI мёртвая ссылка
2. системный промпт из чужого продукта (ALVA baby-care) в JarvisChat
3. снятие `internal` с `DeepSeekDefaults` против правила «internal по умолчанию»

### task7 - контроль уверенности без дообучения

Постановка (`task7/SPEC.md:8-33`): триаж свободного текста -> 4 маршрута `EMERGENCY` / `DOCTOR_SOON` / `SELF_CARE` / `OFF_TOPIC`.
Ошибка несимметрична: пропуск экстренного недопустим, ложная тревога терпима -> при сомнении маршрут поднимается вверх.

Сделано - 4 механизма (задание требовало 2):
1. constraint-based - 14 кодов проверок, вкл. предусловия входа `C_IN_EMPTY` / `C_IN_NO_LETTERS`
2. redundancy - 3 сэмпла t=0.7, голосование по максимуму тяжести
3. self-check - адаптивный триггер (agreement / risk / always)
4. scoring - `confidence_final = 0.5*vote + 0.3*self_check + 0.2*self_reported`, пороги OK>=0.75 / UNSURE>=0.40 / FAIL<0.40

Замер на трёх стендах (`task7/RESULT.md:49-55`):

| Стенд | accuracy baseline -> pipeline | пропущено экстренных | отклонено | p50 | cost |
|---|---|---|---|---|---|
| DeepSeek | 0.8696 -> 0.8043..0.8913 | 0 -> 0 | 0 -> 3 | 1573 -> 5161 мс | 0.0014 -> 0.0041 $ |
| gpt-4o-mini | 0.8261 -> 0.7826 (хуже) | 3 -> 3 | 0 -> 3 | 1371 -> 4268 мс | 0.0071 -> 0.0211 $ |
| Qwen3-1.7B | 0.6087 -> 0.6087 | 4 -> 4 | 0 -> 3 | 1617 -> 9298 мс | локально |

7 находок:
- **А** - пустой ввод даёт `EMERGENCY` с conf 0.822; лечится только проверкой входа (бесплатно)
- **Б** - на сильной модели контроль не поднимает точность
- **В (главный отрицательный результат)** - контроль НЕ снижает пропуски экстренных ни на одной модели (0->0, 3->3, 4->4)
- **Г** - триггер критика по разбросу голосов не срабатывает где нужно; режим «всегда» даёт 1/3 ложных тревог
- **Д** - одиночный прогон не является измерением: разброс accuracy 8.7 п.п. между одинаковыми прогонами; 2 вывода отчёта пришлось исправить
- **Е** - самопроверка той же моделью не даёт независимого сигнала; чужой критик снижает ложные тревоги с 13 до 3
- **Ж (сверх задания)** - дообучение Qwen: accuracy 0.6087 -> 0.8261, пропуски 4 -> 1; дообучение + контроль -> пропуски **0** устойчиво в 3 прогонах

Смоук `harness/smoke.py`: 5/5, код возврата 1 при провале - гейт для CI.

### task8 - роутинг между дешёвой и сильной моделью

Постановка (`task8/SPEC.md`): двухуровневый каскад. Дешёвая - Qwen3-1.7B-4bit + LoRA `alva-triage-qwen-lora` локально ($0).
При триггере -> сильная `deepseek-v4-flash` в облаке.

5 эвристик эскалации: `E_CONF` (порог confidence), `E_STATUS` (UNSURE/FAIL), `E_GUARD` (формат), `E_RISK` (pre-routing по тексту, экономит вызов), `E_LEN` (аномальная длина).
6 стратегий: `only_cheap` / `only_strong` / `route_conf` / `route_status` / `route_risk` / `route_all`.

Результаты (`task8/results/routing_report.json`, 50 кейсов):

| Стратегия | accuracy | missed_emergency | ушло наверх | цена | экономия |
|---|---|---|---|---|---|
| only_cheap | 0.8261 | 1 | 0% | 0 | 100% |
| only_strong | 0.8696 | 0 | 100% | 0.001339 | 0% |
| route_conf (0.85) | 0.8478 | 0 | 40% | 0.000542 | 60% |
| route_status | 0.8043 | **1** | 6% | 0.000095 | 93% |
| route_risk | 0.8478 | 0 | 62% | 0.000873 | 35% |
| **route_all** | **0.8696** | **0** | 68% | 0.000968 | 28% |

- Гейт **не пройден** для `route_status` - теряет экстренный случай
- После первого замера добавлен `E_CONFLICT` (эскалация при расхождении «риск в тексте» vs «спокойный ответ дешёвой»): эскалаций 55% -> 21%, экономия 39% -> 78%
- Находка: облачная MoE-модель недетерминирована даже при temperature=0 (батчинг на стороне провайдера)
- Пороги 0.50/0.65 из контракта мертвы - модель не опускается ниже 0.80 confidence
- `CHAT_SCENARIOS.md` - 8 сценариев ручной проверки чата с ожиданиями по маршруту

В приложение попало: `feature/ai` (`TriageResponseModel/Mapper`, `TriageModel/Route/Status`), `feature/chat` (`TriageDataMapper`, `TriageUiModel`), `feature/settings` (`AiProviderMapper` + провайдер `LOCAL_TRIAGE`).

### task9 - декомпозиция инференса

Постановка (`task9/SPEC.md`): та же задача триажа, два варианта.
- **A - монолит:** 1 вызов, JSON из 5 полей
- **B - цепочка из 3 этапов:** РАЗБОР (только факты, маршрут называть запрещено) -> РЕШЕНИЕ (только факты этапа 1, без исходного текста) -> ОТВЕТ

Результаты (`task9/results/stages_report.json`):

| Метрика | Монолит | Цепочка |
|---|---|---|
| accuracy (3 прогона) | 0.8043..0.8261 | 0.6957..0.7391 |
| missed_emergency (худший) | 2 | 2 |
| ложных тревог | 4 | 5 |
| вызовов модели | 50 | 150 |
| cost_usd | 0.0022 | 0.0049 |
| latency p50 | 1462 мс | 4547 мс |
| нарушений формата | 2 | **0** |

По группам: clean 0.95 / 0.85 · borderline 0.5333 / **0.6000** · noisy **0.9091** / 0.7273

Гипотезы, записанные ДО замера:
1. точнее на borderline - **подтверждена**
2. дороже и медленнее втрое - **подтверждена**
3. устойчивее к шуму - **опровергнута** (0.7273 против 0.9091: «разделение - это фильтр, всегда что-то отрезает»)
4. чинит дефект «возраст как показатель» - **подтверждена**

**Главный вывод:** для этой задачи декомпозиция не окупается - точность ниже на 8-10 пунктов, цена и задержка выше,
а по блокирующей метрике (missed_emergency) паритет. Прод остался на монолите.

Побочно в этой же задаче в приложение добавлены сессии чата:
`feature/chat/.../domain/model/ChatSessionModel.kt`, `presentation/SessionsBottomSheet.kt`, `SessionsViewModel`,
`SessionsUiMapper`, `SessionsDialogs`, use-cases Create/Delete/Load/Observe/Rename/Switch ChatSession.

Ограничения зафиксированы честно: 46 оцениваемых кейсов (разница в 1 кейс = 2 пункта точности); обе ветки на одной
модели `deepseek-chat`; промпты этапов писались за одну итерацию против вылизанного тремя задачами монолитного.

---

## 4. Как проверять

`challenge_advanced/HOWTO_TEST.md` (245 строк) - «Как проверить задачи 7 и 8», 9 шагов от простого к сложному.
`challenge_advanced/check.sh` - без аргументов только читает готовые цифры (бесплатно), с `live` гоняет прогоны.

Итого по HOWTO: <5 центов и ~40 минут на полную проверку.

**task6 и task9 в HOWTO_TEST.md и check.sh не покрыты вообще** (grep «task6» - 0 хитов).
Команды для task9 есть только в `task9/RESULT.md:84-126` и `task9/REPORT.md:174-182`.

Команды task7:
```bash
python3 harness/report.py
python3 harness/run_eval.py --dry-run --mode both
python3 harness/run_eval.py --mode both --workers 6
python3 harness/smoke.py
```

Команды task8:
```bash
python3 harness/router_report.py raw
python3 harness/run_router.py --dry-run --strategy all
python3 harness/run_router.py --strategy route_all --workers 3
```

---

## 5. Сквозная линия task6 -> task9

```
task6  дообучение генерации   -> база 0.4174 -> 0.9163, красные флаги 0/6 -> 6/6
   |    вывод: голый промпт красные флаги не ловит, нужен обученный слой
   v
task7  контроль уверенности   -> находка В: контроль пропуски НЕ лечит (0->0, 3->3, 4->4)
   |    находка Ж: лечит дообучение (4 -> 1 -> 0 вместе с контролем)
   |    т.е. task7 эмпирически подтвердил вывод task6
   v
task8  роутинг cheap/strong   -> route_all: точность сильной модели за 28% её цены, 0 пропусков
   |    + E_CONFLICT: экономия 39% -> 78%
   v
task9  декомпозиция инференса -> отрицательный результат: цепочка хуже монолита на 8-10 п.п.
        прод остался на монолите
```

Каждая задача даёт проверяемый вывод, в том числе отрицательный - что для research-работы правильно.

---

## 6. Верификация находок на текущем HEAD (task9, 7ae0185)

Проверено прямым чтением рабочего дерева, не через `git show`.

### 6.1 Хардкод абсолютного пути - ЖИВ, реальная проблема

`feature/ai/src/commonMain/kotlin/com/jarvis/chat/feature/ai/di/DeepSeekDefaults.kt:11`
```kotlin
const val LOCAL_MODEL_ADAPTER_PATH = "/Users/Victor/models/alva-tpro-lora-ckpt25"
```

Потребляется в `composeApp/src/commonMain/kotlin/com/jarvis/chat/AppConfig.kt:10`.
Repo-wide grep по `*.kt` / `*.kts` (без `build/`, `.git/`, `challenge_advanced/`) - **единственное вхождение `/Users/` во всей кодовой базе**.

Рядом в том же файле `LOCAL_BASE_URL` (`:10`) и `TRIAGE_BASE_URL` (`:17`) - тоже захардкожены, но это `127.0.0.1`, что переносимо. Путь к адаптеру - нет.

**Готовый образец правильного решения уже есть в проекте:** `LOCAL_MODEL_BASE_URL` идёт
`local.properties` -> `androidApp/build.gradle.kts:14,30` -> `BuildConfig` -> `AppConfig` -> DI.
Адаптер должен идти тем же маршрутом.

### 6.2 Два системных промпта разных продуктов - подтверждено, но обосновано

`DeepSeekDefaults.kt:6-7` - `SYSTEM_PROMPT`, английский, Jarvis:
> You are Jarvis, a concise and helpful voice companion...

`DeepSeekDefaults.kt:18-32` - `LOCAL_SYSTEM_PROMPT`, русский, ALVA:
> Вы - ассистент приложения ALVA для родителей детей от 0 до 3 лет...

Технически это **правильно**: локальная LoRA из task6 дообучена именно на ALVA-корпусе с этим форматом ответа.
Подсунуть ей Jarvis-промпт = сломать дообучение (`task6/RUNBOOK.md` - маркеры шаблона).

Продуктово - расхождение: переключение провайдера в настройках меняет и личность ассистента, и язык, и домен.
Это не дефект кода, это следствие того, что challenge-эксперимент вкручен в продуктовое приложение.

### 6.3 Видимость `DeepSeekDefaults` - претензия снимается

`:3` `object DeepSeekDefaults {` - без модификатора, то есть `public`.

`composeApp` и `feature:ai` - **разные Gradle-модули** (`settings.gradle.kts:41,43`). `composeApp` реально
потребляет константы: `AppConfig.kt:9,10,11` и `KoinInitializer.kt:38,47,48,51,52,53,57,58` - 11 обращений.
`internal` сломал бы сборку. `public` здесь корректен по правилу «public только для реального cross-module API».

**Но всплыло другое:** `composeApp` лазает во внутренние дефолты фичи 11 раз и сам собирает `AiProviderConfigModel`.
Детали реализации `feature:ai` вытекли в модуль-обвязку. Правильнее - чтобы `feature:ai` сам отдавал готовый
конфиг провайдера (фабрика/провайдер внутри модуля), а `composeApp` передавал только то, что знает снаружи -
ключ и base-url из `BuildConfig`.

### 6.4 Cleartext-трафик - сделано правильно, претензий нет

`androidApp/src/main/res/xml/network_security_config.xml` - ровно 3 домена (`127.0.0.1`, `10.0.2.2`, `localhost`),
все с `includeSubdomains="false"`.
`androidApp/src/debug/AndroidManifest.xml` - подключает конфиг, лежит в `src/debug` -> только debug-сборка.
Продовый трафик не затронут.

---

## 7. Открытые вопросы / не проверено

- **Гейты не запускались** (мандат read-only): реально ли `router_report.py` и `stages_report.py` возвращают код 1 сейчас - судим только по тексту отчётов.
- **Сборка не проверялась.** `./gradlew :androidApp:assembleDevDebug` не запускался - зелёность текущего `task9` не подтверждена.
- **iOS-ключ пустой:** `MainViewController.kt:16` передаёт `deepSeekApiKey = ""`. Не проверено, осознанно ли это (iOS-сборка вообще не используется?) или дефект.
- **`feature/voice` без DI-модуля** - не проверено, регистрируется ли `SpeechRecognitionController` где-то ещё через Koin.
- `androidApp/src/main/AndroidManifest.xml` напрямую не прочитан - что в нём нет `usesCleartextTraffic`, выведено косвенно (конфиг физически лежит в `src/debug`). Release и флейворные source sets на свой `networkSecurityConfig` не проверялись.
- Хардкоды `/Users/` искались только в `*.kt` / `*.kts`. Properties, yaml, json, shell-скрипты и iOS-таргет (Swift) не проверялись.
- Исходники harness-скриптов (`*.py`) построчно не читаны - логика `E_CONFLICT`, `age_looks_like_metric`, формулы скоринга взяты из прозы отчётов.
- `REPORT.md` task6 (25 КБ) и task7 (40 КБ) целиком не прочитаны - цифры брались из более компактных `RESULT.md` / `CRITERIA.md` / `SOLUTION_MAP.md`.
- `config/detekt/*.yml` и 6 convention-plugins в `build-convention-plugins/` найдены, но не вычитаны.
