# CLAUDE Diff

Сравнение двух конфигураций ассистента (Claude Code) на одинаковых задачах: **обычный** конфиг
(`simple`) vs **оттюнингованный** (`tunning`). Одна и та же фича строилась дважды, разными
изолированными агентами, единственная переменная — конфиг (`global` + `local` CLAUDE.md).

## Что где
```
simple/     ← обычная конфигурация
  global.md   минимальный глобальный ~/.claude/CLAUDE.md (RTK + вычитка текста)
  local.md    обычный проектный CLAUDE.md
tunning/    ← оттюнингованная конфигурация
  global.md   глобальный ~/.claude/CLAUDE.md (Profile/Invariants/Task-States/оркестрация/
              Kotlin-KMP-UDF дефолты + примеры/антипаттерны/шаблон)
  local.md    STRICT проектный CLAUDE.md (нейминг/мапперы/слои/примеры/антипаттерны/шаблон)

01_config-diff.md    чем отличаются конфиги (simple vs tunning)
02_results-diff.md    кто как справился на реальных сборках (метрики + вердикт)
```

## Реализации (отдельные репозитории)
- **simple** → https://github.com/Artofpaganini/jarvis-simple
- **tunning** → https://github.com/Artofpaganini/jarvis-tunning

Обе — Kotlin Multiplatform + Compose Multiplatform чат с DeepSeek + голосовой ввод (STT).
Обе собираются зелёными и проходят линтер; разница — во внутренней архитектуре и конвенциях.
