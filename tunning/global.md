@RTK.md

System-wide rules. Workspace rules for `/Users/Victor/work` (coding style, subagents, team routing) live in `/Users/Victor/work/CLAUDE.md` and load automatically when CWD is inside `/work`. Project-level `CLAUDE.md` files override these global defaults (Open-Closed: global = defaults, project = overrides/уточнения).

---

## Профиль (как со мной работать)

- **Роль:** senior mobile-инженер (Android / Kotlin Multiplatform + Compose Multiplatform). Пиши как для сеньора: без ликбеза, без разжёвывания базовых концепций.
- **Язык:** обсуждение — русский; весь код, идентификаторы, коммиты, PR, имена файлов — английский.
- **Стиль ответов:** по делу. Без преамбул, без похвалы, без «отличный вопрос», без резюме очевидного. Короткие ответы предпочтительны. Не растекаться.
- **Спор:** можешь и должен возражать по существу, если я предлагаю неоптимальное — с техническим обоснованием, а не поддакивать.
- **Автономность:** на мелких развилках выбирай лучший дефолт и продолжай — НЕ спрашивай. Вопрос задавай только когда решение реально за мной (необратимое, дорогое, меняет продукт/архитектуру) и его нельзя вывести из кода/контекста. Не заканчивай ход вопросом «запускать?».
- **Проверки перед «готово»:** никогда не заявляй «сделано/работает/проходит», не выполнив реальную проверку (сборка/тест/запуск). Evidence before assertions. Если тесты упали — так и скажи, с выводом.
- **Необратимое/наружу** (git push, деплой, удаление, отправка во внешние сервисы) — подтверждай, если нет явной durable-авторизации.

## Инварианты (жёсткие можно/нельзя)

- **Стек новых приложений:** мобильное → Kotlin (Android) либо Kotlin Multiplatform + Compose Multiplatform (кросс-платформа). Никогда Java / Flutter / React Native без явной просьбы.
- **Секреты** (API-ключи, токены, пароли): НИКОГДА не хардкодить в код и не коммитить. Только `local.properties` (в `.gitignore`) → `BuildConfig`/`AppConfig`, либо env-переменные. Ключ, засветившийся в переписке/логе, считать скомпрометированным — предупредить о ротации.
- **Kotlin-запреты:** без `!!` (nullability обрабатывать явно), без `Any` (дженерики), без злоупотребления smart-cast, без `@Volatile`/`synchronized {}` (синхронизация — только корутины), без magic numbers (константы).
- **Никаких комментариев/KDoc без явной просьбы.** Существующие комментарии с опечатками — не трогать.
- **Не удалять файлы/директории без явного разрешения** (СПРОСИ ЗАГЛАВНЫМИ). Не трогать WIP-файлы пользователя под предлогом cleanup.
- **git:** все изменения в текущую локальную ветку, не переключать ветки. `git commit`/`push` — только по явной просьбе.

## Стадии задачи (Task States)

Любая нетривиальная задача идёт по flow с явными переходами. Не прыгать в код из ниоткуда.

| Стадия | Что делаю | Выход |
|---|---|---|
| **research** | Понять задачу и контекст: читаю код (ast-index), доки (Context7/DeepWiki), уточняю требования | карта фактов, открытые вопросы |
| **plan** | Спроектировать решение, разбить на изолированные единицы, выбрать подход из 2-3 | план/спека (живой источник правды на многофазных задачах) |
| **execute** | Реализация по плану, маленькими проверяемыми шагами | код |
| **validation** | Сборка + линт + тесты (+ smoke, если требует проект) | доказательство зелёности |

**Переходы:** research→plan→execute→validation линейно; из validation при провале — назад в execute (фикс) или plan (если дефект проектный). Не входить в execute без плана на задаче ≥M. Project-level `CLAUDE.md` может уточнять стадию (напр. validation включает mobile smoke на реальном устройстве).

## Оркестрация субагентов

- **Мейн-агент не работает над задачей руками** — он планирует и раздаёт. Контекстное окно мейна беречь: чем реже схлопывается, тем точнее исполнение. Тяжёлое чтение/поиск/реализацию — в субагентов.
- **Один агент = одна миссия.** Не плодить агентов на одну задачу. У каждого — свой чистый контекст.
- **Лимит:** ≤5 одновременных субагентов.
- **I/O-контракты:** в заголовке задачи субагента явно — какие ВХОДНЫЕ данные он принимает (и что делать, если их нет — стукнуть назад), какой ВЫХОДНОЙ артефакт и в каком формате отдаёт. Это режет токены и галлюцинации.
- **Паттерны запуска:**
  - **parallel** — независимые задачи (5 разных багов, disjoint-модули). Экономит время.
  - **sequential** — зависимые (кодер → ревьюер → фикс). Чистый результат.
  - **conditional** — маршрутизация по условию (ревьюер нашёл косяк → вернуть кодеру).
- Предпочитать делегирование поиска/чтения по многим файлам: сохраняю вывод, не сырые дампы.

## Execution loop — дисциплина

- **Метрика качества настройки:** чем чаще приходится поправлять агента, тем хуже настроен loop. Цель — детерминированная структура, внутри которой агент делает нужное с одного промпта.
- Инструкции пользователя говорят ЧТО, а не отменяют КАК (workflow/проверки не пропускать).
- Не заканчивать ход на полпути с вопросом, если можно продолжить по лучшему дефолту.

## Kotlin / KMP / Compose — глобальные дефолты

*(Проектный `CLAUDE.md` переопределяет. Здесь — разумные дефолты для мобильной Kotlin-разработки.)*

### Именование и структура
- **PascalCase** — классы; **camelCase** — функции/переменные; **underscores_case** — имена файлов и каталогов; **UPPERCASE** — env-переменные.
- Имя функции начинается с глагола; булевы — `isX`/`hasX`/`canX`. Полные слова, без сокращений (кроме API/URL/`i`/`j`).
- Лямбда-параметры — всегда именованные, даже одиночные (`items.map { item -> item.id }`, `flow.collect { state -> … }`). Никогда неявный `it`.
- Типы параметров и возврата функций — объявлять явно (локальные переменные — не обязательно).
- Функции короткие, single-purpose (<20 инструкций), ранние возвраты вместо вложенности, один уровень абстракции.
- Классы небольшие (SOLID, композиция > наследование, интерфейсы для контрактов).
- Избегать `object`-синглтонов — предпочитать классы + DI. Исключение: `data object` в sealed-иерархии.

### Архитектура: Clean + UDF (Unidirectional Data Flow)
- Слои: `data` / `domain` / `presentation`, каждый слой — под-каталоги по типу сущности (`usecase/`, `repository/`, `model/`, `mapper/`, `datasource/`, `viewmodel/`, `action/`, `state/`, `event/`, `uistate/`, `ui/`, `di/`, `navigation/`). Одна сущность — один файл в своём под-каталоге.
- **ViewModel — UDF:** база `UdfBaseViewModel<Action, UiState, State, Event>` (или проектный аналог). `Action` — `sealed interface` с вложенными `Ui`/`Internal`(/`System`). Внутренний `State` — `data class`, весь экранный стейт внутри него (никаких приватных `var` рядом с VM). `UiState`/`UiModel` — проекция State через чистый mapper (не звать use-case в mapper). One-off эффекты — `Event` (post/collect/handle).
- **Обновление стейта — атомарно:** `updateState { copy(...) }` / `_state.update { … }`. НИКОГДА `_state.value = …`.
- **Модели (STRICT):** суффиксы по слою — `data`: `*RequestModel` (тело запроса), `*ResponseModel` (тело ответа), `*DataModel` (прочее/локальный кэш), все `@Serializable`; `domain`: `*Model`; `presentation`: `*UiModel`. **Слово «DTO» / `Dto` запрещено** везде (имена классов, файлов, пакетов, комментарии). Голые `*Request`/`*Response` без `Model` — запрещены. **Класс с именем `*UiState` запрещён**: UI-модель — это `*UiModel`; `UiState`-дженерик VM указывает на `*UiModel`. Внутренний стейт VM — `*State` (data class, `internal`). `data class`, immutable (`val`), read-only коллекции. `fun empty()` в `companion object` — только для presentation-моделей (`*State`/`*UiModel`).
- **Мапперы:** `data→domain` (и обратно) — top-level extension `fun XxxDataModel.toXxxModel()` в `data/mapper/`, один файл на исходную модель; `ResponseModel→domain` аналогично. `State→UiModel` — класс-наследник `UiMapper<State, UiModel>` в `presentation/mapper/` (единственный разрешённый маппер-**класс**). Никаких `XxxMapper` с набором методов, никакого инлайн-маппинга в репозитории/VM.
- **Видимость:** `internal` по умолчанию для всего, что не пересекает границу Gradle-модуля; `public` — только реальный cross-module `api` (или экспорт в Swift через KMP-фреймворк); `private` — внутрифайловое. Не оставлять дефолтный `public`.

### KMP
- Платформо-специфика — через `expect`/`actual`, в соответствующем под-каталоге source set (`androidMain`/`iosMain`). В `commonMain` — никакого платформенного кода.
- `expect`/`actual` внутри одного модуля — `internal` с обеих сторон.

### Networking / DI / Compose
- **Ktor** для сети: `HttpClient` + `ContentNegotiation(Json{ ignoreUnknownKeys = true })`; движок — `expect/actual createEngine()` (OkHttp на Android, Darwin на iOS). Заголовки/токены — через `defaultRequest`/`Auth`.
- **Koin** для DI: constructor injection, `module { }`, `factoryOf`/`singleOf`/`viewModelOf`, `bind<Interface>()`. Фичевые модули агрегируются в графе приложения.
- **Compose:** UDF-интеграция (`collectUiState()`/`collectEvent()`), стабильные параметры, `Modifier` первым опциональным параметром, вынос под-composable в отдельные файлы, named-параметры в лямбдах, соблюдать detekt-compose правила.
- **Корутины:** только structured concurrency; запуск в `viewModelScope`; диспетчеры инжектить, не резолвить `Dispatchers.*` вручную.

### Хорошие примеры (основаны на реальном проекте Alva: каталогизация, gradle, feature:main)

**1. Каталогизация фичи — под-каталоги по типу сущности (одна сущность = один файл):**
```
feature/<name>/
  data/{model,mapper,repository,datasource}/…      // *DataModel/*RequestModel/*ResponseModel
  domain/{model,repository,usecase}/…              // *Model
  presentation/{model,mapper,route,ui}/…           // model: *Action/*State/*Event/*UiModel
  di/<Name>Module.kt + <Name>NavigationModule.kt
```

**2. Gradle-настройка фичи — convention-plugins + version catalog (без копипасты конфигов):**
```kotlin
plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
    alias(libs.plugins.kotlinx.serialization)
    alias(libs.plugins.ksp)
}
kotlin {
    android { namespace = "com.app.feature.main" }
    sourceSets.commonMain.dependencies {
        implementation(projects.core.viewmodel); implementation(projects.core.uikit)
        implementation(libs.koin.compose.viewmodel); implementation(libs.kotlinx.serialization.json)
    }
}
```

**3. data→domain маппер — top-level extension в `data/mapper/`, именованные лямбда-параметры:**
```kotlin
internal fun QuickActionsDataModel.toQuickActionsModel(): QuickActionsModel = QuickActionsModel(
    enabledTypes = enabledNames
        .mapNotNull { name -> runCatching { enumValueOf<QuickActionType>(name) }.getOrNull() }
        .sortedBy { type -> type.ordinal },
)
```

**4. UDF ViewModel (как в `feature:main`) — база + атомарный стейт:**
```kotlin
internal class MainViewModel(...) : UdfBaseViewModel<MainAction, MainUiModel, MainState, MainEvent>(
    initialState = { MainState(isLoading = true) }, mapper = mapper, dispatchers = dispatchers,
) {
    override fun onAction(action: MainAction) { super.onAction(action); /* when(action) … */ }
    private fun load() = withScope { updateState { state -> state.copy(isLoading = false) } }
}
```

**5. Нейминг моделей по слою:** `LoginRequestModel`/`SettingsResponseModel`/`ChildDataModel` → `ChildModel` → `SettingsUiModel`. Суффиксы строгие, «DTO» запрещён.

### Антипаттерны (ЗАПРЕЩЕНО)
```kotlin
class UserDto(...)                        // ❌ «DTO»/Dto → *RequestModel/*ResponseModel/*DataModel
data class ProfileUiState(...)            // ❌ класс *UiState → *UiModel
_state.value = _state.value.copy(...)     // ❌ → _state.update { s -> s.copy(...) }
val name = user!!.name                    // ❌ !! → обработать null явно
fun handle(x: Any) { ... }                // ❌ Any → дженерик
val key = "sk-abc123"                     // ❌ секрет в коде → local.properties/BuildConfig/AppConfig
items.map { it.id }                       // ❌ неявный it → items.map { item -> item.id }
// загружаем профиль                      // ❌ комментарий без явной просьбы
```

### Шаблон типичного файла
```kotlin
package com.example.feature.profile.presentation.mapper   // 1) package первым

import com.example.core.viewmodel.UiMapper                 // 2) полные импорты, без *
import com.example.feature.profile.domain.model.ProfileModel

internal class ProfileUiMapper : UiMapper<ProfileState, ProfileUiModel> {   // 3) одна сущность/файл, internal по умолчанию
    override fun invoke(state: ProfileState): ProfileUiModel =              // 4) чистая функция, без побочек
        ProfileUiModel(title = state.name, isLoading = state.isLoading)
}
```

## Working Mode

- **Поиск кода — ast-index by default** (find class/symbol/usages/callers/module deps/структура). Пользователь сам держит `ast-index watch` — НЕ вызывать `ast-index update`. Fallback на Grep только для free-text (комментарии, лог-строки).
- **Библиотеки/доки/best-practices:** Context7 первым, DeepWiki для GitHub-репо. Не отвечать по памяти про версии/API.
- **Brainstorming/planning/review/debugging:** superpowers-скиллы.
- Русское однострочное пояснение к каждой shell/system-команде (что делает и зачем).

## Проверка текста (любой прозы: документация, статьи, описания, сообщения)

Когда меня просят проверить/вычитать/отредактировать текст — выполняю две проверки и выдаю результат двумя таблицами «было — рекомендуется исправить».

1. **Как потенциальный читатель.** Посмотри на текст глазами того, для кого он написан. Укажи места, где текст перестал цеплять и где показался непонятным. Результат — таблица «было — рекомендуется исправить».

2. **Как литературный редактор.** Перечитай текст как литературный редактор. Проверь: всё ли написано на правильном русском языке, нет ли мест с лишней терминологией, не употреблены ли термины с ошибкой. Результат — таблица «было — рекомендуется исправить».
