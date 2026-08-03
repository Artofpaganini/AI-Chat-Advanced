"""L3_OUTPUT_GUARD - детерминированный фильтр на выходе, не LLM (контракт раздел 5).

Ловит пять вещей, которые не должны уйти пользователю ни при каких обстоятельствах: маркеры
системного промпта, дозировку/диагноз/отговор от врача (только alva), PII, подозрительные ссылки,
смену личности (2026-08-03 - "Developer Mode enabled"/"DAN Mode enabled" раньше проходили насквозь,
потому что guard проверял всё, кроме PERSONA_BREAK). Срабатывание = весь ответ заменяется на
OUTPUT_GUARD_FALLBACK целиком, частичная вырезка не делается - лекция прямо говорит, что output
guard режет всё лишнее, а не пытается угадать полезную часть.
"""

import re
from typing import List, Tuple

import detectors
import spec11

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\-\s()]{8,14}\d)")
CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


def guard_reasons(response_text: str, target: str) -> List[str]:
    reasons: List[str] = []
    leak_success, _ = detectors.detect_leak(response_text, target)
    if leak_success:
        reasons.append("leak_markers")
    if target == spec11.TARGET_ALVA:
        bypass, reason = detectors.detect_safety_bypass(response_text, target)
        if bypass:
            reasons.append("safety_bypass_%s" % reason)
    if EMAIL_PATTERN.search(response_text) or PHONE_PATTERN.search(response_text) or CARD_PATTERN.search(
        response_text
    ):
        reasons.append("pii")
    if URL_PATTERN.search(response_text):
        reasons.append("suspicious_url")
    if detectors.detect_persona_break(response_text, target):
        reasons.append("persona_break")
    return reasons


def apply(response_text: str, target: str) -> Tuple[str, List[str]]:
    reasons = guard_reasons(response_text, target)
    if reasons:
        return spec11.OUTPUT_GUARD_FALLBACK, reasons
    return response_text, []
