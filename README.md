# AI-Chat-Advanced

Рабочая база: Kotlin Multiplatform + Compose Multiplatform чат с AI-ассистентом (DeepSeek) +
голосовой ввод (STT). Собирается зелёной (`./gradlew :androidApp:assembleDevDebug`).
Проектные правила — в корневом `CLAUDE.md` (оттюнингованная конфигурация).

## Код
- `androidApp/` · `composeApp/` · `core/` · `feature/` (chat / ai / voice) — приложение
- `build-convention-plugins/` · `config/` · gradle-обвязка — сборка
- `CLAUDE.md` — активные проектные правила (Clean + UDF, STRICT-конвенции)

## challenge_advanced/ — материалы челленджа
```
challenge_advanced/task1/
  simple/     ← обычная конфигурация
    global.md   минимальный глобальный ~/.claude/CLAUDE.md
    local.md    обычный проектный CLAUDE.md
  tunning/    ← оттюнингованная конфигурация
    global.md   глобальный ~/.claude/CLAUDE.md (Profile/Invariants/Task-States/оркестрация/
                Kotlin-KMP-UDF дефолты + примеры/антипаттерны/шаблон)
    local.md    STRICT проектный CLAUDE.md
  01_config-diff.md    чем отличаются конфиги (simple vs tunning)
  02_results-diff.md   кто как справился на реальных сборках (метрики + вердикт)
```

Task 1: одна и та же фича строилась дважды разными изолированными агентами; единственная
переменная — конфиг (`global` + `local` CLAUDE.md). Оба варианта зелёные и проходят линтер;
разница — во внутренней архитектуре и конвенциях (вердикт — в `02_results-diff.md`).

Реализации-исходники: [jarvis-simple](https://github.com/Artofpaganini/jarvis-simple) ·
[jarvis-tunning](https://github.com/Artofpaganini/jarvis-tunning).
