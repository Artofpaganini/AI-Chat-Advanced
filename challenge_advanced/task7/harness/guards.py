"""Механизм 1 - Constraint-based: детерминированные проверки без второго вызова модели.

check_input - предусловия входа из SPEC раздел 3.1, работают ДО обращения к модели.
check_reply и check_critic_reply - проверки выхода, коды совпадают с SPEC раздел 3.
Отдельно отмечается мягкий признак W_FENCED: модель обернула JSON в markdown-забор.
Это не нарушение решения, но повод знать, как часто модель ломает формат.
"""

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import spec7

FENCE_PATTERN = re.compile(
    r"^\s*```[a-zA-Z0-9_+-]*[ \t]*\r?\n?(?P<body>.*?)\r?\n?\s*```\s*$", re.DOTALL
)


@dataclass
class GuardResult:
    ok: bool
    violations: List[str]
    parsed: Optional[Dict[str, Any]]


def strip_code_fence(raw_text: str) -> Tuple[str, bool]:
    match = FENCE_PATTERN.match(raw_text)
    if match is None:
        return raw_text, False
    return match.group("body"), True


def parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(text)
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def is_integer(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, int)


def has_hard_violation(violations: List[str]) -> bool:
    for code in violations:
        if not code.startswith(spec7.SOFT_PREFIX):
            return True
    return False


def has_letter(text: str) -> bool:
    for char in text:
        if char.isalpha():
            return True
    return False


def check_input(text: str) -> GuardResult:
    value = text if isinstance(text, str) else ""
    if not value.strip():
        return GuardResult(False, [spec7.C_IN_EMPTY], None)
    if not has_letter(value):
        return GuardResult(False, [spec7.C_IN_NO_LETTERS], None)
    return GuardResult(True, [], None)


def check_keys(parsed: Dict[str, Any], expected_keys) -> List[str]:
    if set(parsed.keys()) != set(expected_keys):
        return [spec7.C_KEYS]
    return []


def check_reply_types(parsed: Dict[str, Any]) -> List[str]:
    route = parsed.get("route")
    red_flags = parsed.get("red_flags")
    age_months = parsed.get("age_months")
    confidence = parsed.get("confidence")
    reason = parsed.get("reason")
    if not isinstance(route, str):
        return [spec7.C_TYPES]
    if not isinstance(red_flags, list):
        return [spec7.C_TYPES]
    if age_months is not None and not is_integer(age_months):
        return [spec7.C_TYPES]
    if not is_number(confidence):
        return [spec7.C_TYPES]
    if not isinstance(reason, str):
        return [spec7.C_TYPES]
    return []


def check_route_enum(parsed: Dict[str, Any]) -> List[str]:
    if parsed.get("route") not in spec7.ROUTES:
        return [spec7.C_ROUTE_ENUM]
    return []


def check_confidence_range(parsed: Dict[str, Any]) -> List[str]:
    confidence = parsed.get("confidence")
    if not is_number(confidence):
        return [spec7.C_CONF_RANGE]
    if confidence < 0.0 or confidence > 1.0:
        return [spec7.C_CONF_RANGE]
    return []


def check_age_range(parsed: Dict[str, Any]) -> List[str]:
    age_months = parsed.get("age_months")
    if age_months is None:
        return []
    if not is_integer(age_months):
        return [spec7.C_AGE_RANGE]
    if age_months < spec7.MIN_AGE_MONTHS or age_months > spec7.MAX_AGE_MONTHS:
        return [spec7.C_AGE_RANGE]
    return []


def check_flags_shape(parsed: Dict[str, Any]) -> List[str]:
    red_flags = parsed.get("red_flags")
    if not isinstance(red_flags, list):
        return [spec7.C_FLAGS_SHAPE]
    if len(red_flags) > spec7.MAX_RED_FLAGS:
        return [spec7.C_FLAGS_SHAPE]
    for flag in red_flags:
        if not isinstance(flag, str):
            return [spec7.C_FLAGS_SHAPE]
        if len(flag) > spec7.MAX_FLAG_CHARS:
            return [spec7.C_FLAGS_SHAPE]
    return []


def check_reason_length(parsed: Dict[str, Any]) -> List[str]:
    reason = parsed.get("reason")
    if not isinstance(reason, str):
        return [spec7.C_REASON_LEN]
    if len(reason) < spec7.MIN_REASON_CHARS or len(reason) > spec7.MAX_REASON_CHARS:
        return [spec7.C_REASON_LEN]
    return []


def check_invariants(parsed: Dict[str, Any]) -> List[str]:
    route = parsed.get("route")
    if route not in spec7.ROUTES:
        return []
    red_flags = parsed.get("red_flags")
    flags = red_flags if isinstance(red_flags, list) else []
    confidence = parsed.get("confidence")
    age_months = parsed.get("age_months")
    violations = []
    if route == spec7.ROUTE_EMERGENCY:
        if not flags:
            violations.append(spec7.C_INV_EMERGENCY_FLAGS)
        if not is_number(confidence) or confidence < 0.5:
            violations.append(spec7.C_INV_CONF_FLOOR)
    if route == spec7.ROUTE_SELF_CARE and flags:
        violations.append(spec7.C_INV_SELFCARE_FLAGS)
    if route == spec7.ROUTE_OFF_TOPIC and (flags or age_months is not None):
        violations.append(spec7.C_INV_OFFTOPIC_CLEAN)
    return violations


def check_reply(raw_text: str) -> GuardResult:
    violations: List[str] = []
    text, fenced = strip_code_fence(raw_text or "")
    if fenced:
        violations.append(spec7.W_FENCED)
    parsed = parse_json_object(text)
    if parsed is None:
        violations.append(spec7.C_JSON)
        return GuardResult(False, violations, None)
    violations.extend(check_keys(parsed, spec7.REPLY_KEYS))
    violations.extend(check_reply_types(parsed))
    violations.extend(check_route_enum(parsed))
    violations.extend(check_confidence_range(parsed))
    violations.extend(check_age_range(parsed))
    violations.extend(check_flags_shape(parsed))
    violations.extend(check_reason_length(parsed))
    violations.extend(check_invariants(parsed))
    return GuardResult(not has_hard_violation(violations), violations, parsed)


def check_critic_types(parsed: Dict[str, Any]) -> List[str]:
    if not isinstance(parsed.get("verdict"), str):
        return [spec7.C_CRITIC_TYPES]
    if not isinstance(parsed.get("risk_missed"), bool):
        return [spec7.C_CRITIC_TYPES]
    if not isinstance(parsed.get("note"), str):
        return [spec7.C_CRITIC_TYPES]
    return []


def check_critic_reply(raw_text: str) -> GuardResult:
    violations: List[str] = []
    text, fenced = strip_code_fence(raw_text or "")
    if fenced:
        violations.append(spec7.W_FENCED)
    parsed = parse_json_object(text)
    if parsed is None:
        violations.append(spec7.C_CRITIC_JSON)
        return GuardResult(False, violations, None)
    if set(parsed.keys()) != set(spec7.CRITIC_KEYS):
        violations.append(spec7.C_CRITIC_KEYS)
    violations.extend(check_critic_types(parsed))
    if parsed.get("verdict") not in spec7.VERDICTS:
        violations.append(spec7.C_CRITIC_VERDICT_ENUM)
    note = parsed.get("note")
    if not isinstance(note, str) or len(note) > spec7.MAX_NOTE_CHARS:
        violations.append(spec7.C_CRITIC_NOTE_LEN)
    return GuardResult(not has_hard_violation(violations), violations, parsed)
