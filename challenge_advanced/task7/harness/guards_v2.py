"""Проверки формата для версии 2: те же коды, расширенный набор маршрутов.

guards.py заморожен вместе со spec7 - он знает только четыре маршрута. Здесь переиспользуются
его же проверки типов, диапазонов и длин, а подменяются ровно два места: перечисление маршрутов
и инварианты, потому что у DATA_INSIGHT свой запрет на red_flags.
"""

import os
import sys
from typing import Any, Dict, List

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import guards
import spec7
import spec_v2


def check_route_enum(parsed: Dict[str, Any]) -> List[str]:
    if parsed.get("route") not in spec_v2.ROUTES:
        return [spec7.C_ROUTE_ENUM]
    return []


def check_invariants(parsed: Dict[str, Any]) -> List[str]:
    route = parsed.get("route")
    if route not in spec_v2.ROUTES:
        return []
    red_flags = parsed.get("red_flags")
    flags = red_flags if isinstance(red_flags, list) else []
    confidence = parsed.get("confidence")
    age_months = parsed.get("age_months")
    violations: List[str] = []
    if route == spec7.ROUTE_EMERGENCY:
        if not flags:
            violations.append(spec7.C_INV_EMERGENCY_FLAGS)
        if not guards.is_number(confidence) or confidence < 0.5:
            violations.append(spec7.C_INV_CONF_FLOOR)
    if route in (spec7.ROUTE_SELF_CARE, spec_v2.ROUTE_DATA_INSIGHT) and flags:
        violations.append(spec7.C_INV_SELFCARE_FLAGS)
    if route == spec7.ROUTE_OFF_TOPIC and (flags or age_months is not None):
        violations.append(spec7.C_INV_OFFTOPIC_CLEAN)
    return violations


def check_reply(raw_text: str) -> guards.GuardResult:
    violations: List[str] = []
    text, fenced = guards.strip_code_fence(raw_text or "")
    if fenced:
        violations.append(spec7.W_FENCED)
    parsed = guards.parse_json_object(text)
    if parsed is None:
        violations.append(spec7.C_JSON)
        return guards.GuardResult(False, violations, None)
    violations.extend(guards.check_keys(parsed, spec7.REPLY_KEYS))
    violations.extend(guards.check_reply_types(parsed))
    violations.extend(check_route_enum(parsed))
    violations.extend(guards.check_confidence_range(parsed))
    violations.extend(guards.check_age_range(parsed))
    violations.extend(guards.check_flags_shape(parsed))
    violations.extend(guards.check_reason_length(parsed))
    violations.extend(check_invariants(parsed))
    return guards.GuardResult(not guards.has_hard_violation(violations), violations, parsed)
