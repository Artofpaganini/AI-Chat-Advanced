"""Порт HistoryMessageMapper.kt:15-27 (toRequestContext) - окно контекста реального импорта.

Применяется только к V1_SUMMARY (настоящий канал). У V2/V3 нет реального приложенческого пути,
поэтому этой обрезки к ним применять нечего - придумывать несуществующее поведение не будем.

Дословная логика: берутся последние MAX_CONTEXT_MESSAGES сообщений, дальше они обходятся от
НОВЕЙШЕГО к СТАРЕЙШЕМУ, накапливая длину. Первое (новейшее) сообщение добавляется всегда - проверка
"trimmedMessages.isNotEmpty()" делает её пустой на первом шаге. Значит новейшее сообщение проходит
целиком, каким бы длинным оно ни было, а следующие (более старые) обрезаются по общему бюджету
символов - как только бюджет превышен, все более старые сообщения отбрасываются разом.
"""

from typing import Any, Dict, List

import spec12


def apply_context_window(turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    recent = turns[-spec12.MAX_CONTEXT_MESSAGES:]
    trimmed: List[Dict[str, Any]] = []
    total_chars = 0
    for turn in reversed(recent):
        text_length = len(turn.get("content", ""))
        next_total_chars = total_chars + text_length
        if trimmed and next_total_chars > spec12.MAX_CONTEXT_CHARS:
            break
        trimmed.append(turn)
        total_chars = next_total_chars
    return list(reversed(trimmed))
