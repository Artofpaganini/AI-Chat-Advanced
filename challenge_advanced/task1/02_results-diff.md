# Results diff — кто как справился

Одна и та же фича строилась дважды свежими изолированными агентами. Метрики — из реального кода
(`grep`/`find`, src без `build/`). Проведено два раунда.

---

## Раунд 1 — простой чат (DeepSeek + TTS)

| Метрика | simple | tunning |
|---|---:|---:|
| Kotlin-файлов в фиче | 12 | **25** |
| «DTO»/`Dto` | `DeepSeekDto` | 0 → `*RequestModel/*ResponseModel` |
| класс `*UiState` | `AssistantUiState` | 0 → `*UiModel` |
| выделенные мапперы | 0 (инлайн) | 3 (`toXxx()` + `UiMapper`) |
| use-case слой | 0 | `SendMessageUseCase` |
| под-каталоги в `data/` | 0 (плоско) | `datasource/mapper/model/repository` |
| комментарии без запроса | 8 | 0 |
| `internal` | 11 | 23 |
| видимость ViewModel | `public` | `internal` |
| build + iOS + lint | ✅ green | ✅ green |

---

## Раунд 2 — модульный voice-chat (DeepSeek + STT + TTS, подмодули `feature/`)

Жёсткое требование обоим: разбить на Gradle-подмодули (`feature:chat` / `feature:ai` / `feature:voice`).

| Метрика | simple | tunning |
|---|---:|---:|
| src Kotlin-файлов | 19 | **33** |
| модули (требование) | ✅ 3 (ai/chat/voice) | ✅ 3 + вынес `core:viewmodel` |
| **UDF-база** | ❌ нет (plain `StateFlow`) | ✅ **сам построил `UdfBaseViewModel`** |
| data-слой | плоский (4 файла) | `datasource/`+`mapper/`+`model/`+`repository/` |
| нейминг сети | `DeepSeekDto` | **5× `*RequestModel/*ResponseModel`, 0 Dto** |
| класс `*UiState` | `ChatUiState` | 0 → `*UiModel` (6) |
| мапперы | 0 (инлайн) | 3 |
| комментарии без запроса | ~75 | 0 |
| `internal` | 11 | 23 |
| видимость ViewModel | `public` | `internal` |
| build + iOS + lint | ✅ green | ✅ green |

---

## Вердикт: tunning справился лучше

Оба варианта в обоих раундах: **компилируются, проходят линтер, выполняют все функциональные
требования** (чат, DeepSeek, голосовой ввод, модуляризация). Разница — исключительно во внутренней
архитектуре и соответствии конвенциям, и она стабильно в пользу `tunning`.

- **simple** → «работает, но наивно»: плоская структура, `Dto`, класс `*UiState`, инлайн-маппинг,
  публичные VM, лишние комментарии, без слоя use-case и без UDF-базы.
- **tunning** → production Clean + UDF: слои с под-каталогами, строгий нейминг моделей, выделенные
  мапперы, `internal` по умолчанию, ноль незапрошенных комментариев; во 2-м раунде агент даже
  **построил собственный UDF-фреймворк**, которого не было в скелете.

**Ключевой инсайт:** даже обычный конфиг выполнил жёсткие функциональные требования (модуляризацию) —
значит конфиг определяет **качество и стиль**, а не факт-выполнения. Он детерминированно тянет код к
production-конвенциям с одного промпта, без итераций и правок.

### Что дало наибольший эффект
1. STRICT-нейминг моделей (запрет DTO/`*UiState`, суффиксы `*RequestModel`/`*UiModel`).
2. Правило мапперов (extension + `UiMapper`, без инлайна).
3. Clean-слои с под-каталогами по сущности.
4. «Без комментариев без запроса».
5. `internal` по умолчанию.
6. UDF-паттерн + Task-States/execution-loop дисциплина (агент шёл research→plan→execute→validation).
