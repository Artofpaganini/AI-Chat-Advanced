# Config diff — simple vs tunning

Переменная эксперимента. `simple` и `tunning` отличаются ТОЛЬКО содержимым CLAUDE.md
(глобального и локального). Всё остальное (задача, скелет, технические факты) — константа.

## Объём
| Файл | simple | tunning |
|---|---:|---:|
| `global.md` | 11 строк | 175 строк |
| `local.md` | 28 строк | 93 строки |

## Глобальный конфиг (`global.md`)
| Секция | simple | tunning |
|---|---|---|
| RTK / вычитка текста | ✅ | ✅ (сохранено, Open-Closed) |
| **Профиль** (роль, стиль, автономность, evidence-before-done) | ❌ | ✅ |
| **Инварианты** (Kotlin-only, no-hardcode-secrets, no `!!`/`Any`, no-comments) | ❌ | ✅ |
| **Task-States** (research→plan→execute→validation + переходы) | ❌ | ✅ |
| **Оркестрация субагентов** (≤5, one-agent-one-mission, I/O-контракты, parallel/sequential/conditional) | ❌ | ✅ |
| **Execution-loop дисциплина** | ❌ | ✅ |
| **Kotlin/KMP/Compose дефолты** (naming, UDF, `updateState`, модели, мапперы, visibility, expect/actual, Ktor/Koin/Compose) | ❌ | ✅ |
| **Примеры / антипаттерны / шаблон файла** (Alva-grounded) | ❌ | ✅ |

## Локальный конфиг (`local.md`)
| Аспект | simple (обычный) | tunning (STRICT) |
|---|---|---|
| Стиль | модест: стек, команды сборки, «пиши чисто» | production-правила поверх глобала |
| Архитектура | не задана (агент решает сам) | Clean + UDF, генерик-порядок, поток данных |
| Каталогизация фичи | «раздели логику и UI» | под-каталоги по типу сущности (`data/{model,mapper,datasource,repository}` …) |
| Нейминг моделей | — | STRICT: `*RequestModel/*ResponseModel/*DataModel/*Model/*UiModel`, «DTO» запрещён, класс `*UiState` запрещён |
| Мапперы | — | `toXxx()` extension + `UiMapper`-класс, без инлайна |
| Видимость | — | `internal` по умолчанию |
| Примеры/антипаттерны/шаблон | ❌ | ✅ (реальные файлы проекта) |

## Суть
`simple` даёт ассистенту почти нулевой архитектурный контекст → он опирается на дефолты и «здравый смысл».
`tunning` детерминированно задаёт конвенции → ассистент воспроизводит их с одного промпта, без правок.
Как это сказалось на коде — см. `02_results-diff.md`.
