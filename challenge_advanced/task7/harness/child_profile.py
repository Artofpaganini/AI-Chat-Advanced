"""Данные ребёнка: разбор из текста и из профиля, слияние, блок для промпта и сравнение.

Источников два. Первый - цифры прямо в сообщении родителя: нам 7 месяцев, весим 8.1 кг,
рост 68 см. Второй - необязательное поле child_profile в теле запроса. Сообщение главнее:
оно свежее профиля, и просить то, что человек уже написал, нельзя.

Все поля необязательные, чужие ключи выбрасываются, значения вне разумных границ не
принимаются - вместо падения запись уходит в issues, а ответ строится по тем полям,
что остались.

Цифры ребёнка персональные. Наружу этот модуль отдаёт только имена заполненных полей
и источник данных, значения живут внутри ответа конкретному родителю и в логи не попадают.
"""

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import spec_v2

ISSUE_NOT_OBJECT = "профиль не объект JSON"
ISSUE_UNKNOWN_FIELD = "неизвестное поле %s"
ISSUE_BAD_TYPE = "поле %s не число"
ISSUE_OUT_OF_RANGE = "поле %s вне допустимых границ"
ISSUE_BAD_NOTES = "поле notes не строка"

NUMERIC_FIELDS = (
    spec_v2.FIELD_AGE_MONTHS,
    spec_v2.FIELD_WEIGHT_KG,
    spec_v2.FIELD_HEIGHT_CM,
    spec_v2.FIELD_SLEEP_HOURS,
    spec_v2.FIELD_FEEDINGS,
)

INTEGER_FIELDS = (spec_v2.FIELD_AGE_MONTHS, spec_v2.FIELD_FEEDINGS)

TEXT_LETTER_YO = "ё"
TEXT_LETTER_YE = "е"

AGE_WORD_RULES = tuple(
    (re.compile(pattern), months) for pattern, months in spec_v2.AGE_WORD_VALUES
)
AGE_RULES = tuple((re.compile(pattern), kind) for pattern, kind in spec_v2.AGE_PATTERNS)

NUMBER_WORD_ALTERNATIVES = "|".join(sorted(spec_v2.NUMBER_WORDS, key=len, reverse=True))

AGE_WORD_NUMBER_RULES = tuple(
    (re.compile(pattern % NUMBER_WORD_ALTERNATIVES), kind)
    for pattern, kind in spec_v2.AGE_WORD_NUMBER_PATTERNS
)

WEIGHT_MASK_RULES = tuple(re.compile(pattern) for pattern in spec_v2.WEIGHT_MASK_PATTERNS)
WEIGHT_RULES = tuple((re.compile(pattern), kind) for pattern, kind in spec_v2.WEIGHT_PATTERNS)
HEIGHT_RULES = tuple((re.compile(pattern), kind) for pattern, kind in spec_v2.HEIGHT_PATTERNS)
SLEEP_RULES = tuple((re.compile(pattern), kind) for pattern, kind in spec_v2.SLEEP_PATTERNS)
FEEDING_RULES = tuple((re.compile(pattern), kind) for pattern, kind in spec_v2.FEEDING_PATTERNS)


@dataclass
class ChildProfile:
    values: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    supplied: bool = False

    @property
    def present(self) -> bool:
        return bool(self.values)

    @property
    def names(self) -> List[str]:
        return [name for name in spec_v2.CHILD_PROFILE_FIELDS if name in self.values]

    @property
    def age_months(self) -> Optional[int]:
        value = self.values.get(spec_v2.FIELD_AGE_MONTHS)
        if isinstance(value, int):
            return value
        return None

    @property
    def has_metrics(self) -> bool:
        for name in (spec_v2.FIELD_WEIGHT_KG, spec_v2.FIELD_HEIGHT_CM, spec_v2.FIELD_SLEEP_HOURS):
            if name in self.values:
                return True
        return False


def is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def number_text(value: Any) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def sanitize(raw: Any) -> ChildProfile:
    if raw is None:
        return ChildProfile()
    if not isinstance(raw, dict):
        return ChildProfile(issues=[ISSUE_NOT_OBJECT], supplied=True)
    values: Dict[str, Any] = {}
    issues: List[str] = []
    for key, value in raw.items():
        if key not in spec_v2.CHILD_PROFILE_FIELDS:
            issues.append(ISSUE_UNKNOWN_FIELD % key)
            continue
        if value is None:
            continue
        if key == spec_v2.FIELD_NOTES:
            if not isinstance(value, str):
                issues.append(ISSUE_BAD_NOTES)
                continue
            text = value.strip()[: spec_v2.MAX_NOTES_CHARS]
            if text:
                values[key] = text
            continue
        if not is_number(value):
            issues.append(ISSUE_BAD_TYPE % key)
            continue
        low, high = spec_v2.CHILD_PROFILE_LIMITS[key]
        if value < low or value > high:
            issues.append(ISSUE_OUT_OF_RANGE % key)
            continue
        values[key] = int(round(value)) if key in INTEGER_FIELDS else float(value)
    return ChildProfile(values=values, issues=issues, supplied=True)


def normalize_text(text: str) -> str:
    value = text if isinstance(text, str) else ""
    return value.lower().replace(TEXT_LETTER_YO, TEXT_LETTER_YE)


def to_number(raw: str) -> Optional[float]:
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def in_limits(field_name: str, value: float) -> bool:
    low, high = spec_v2.CHILD_PROFILE_LIMITS[field_name]
    return low <= value <= high


def match_age(text: str) -> Optional[int]:
    for pattern, months in AGE_WORD_RULES:
        if pattern.search(text) is not None:
            return months
    for pattern, kind in AGE_RULES:
        found = pattern.search(text)
        if found is None:
            continue
        first = to_number(found.group(1))
        if first is None:
            continue
        if kind == "years_months":
            second = to_number(found.group(2))
            months = first * spec_v2.UNIT_MONTHS_IN_YEAR + (second or 0.0)
        elif kind == "years":
            months = first * spec_v2.UNIT_MONTHS_IN_YEAR
        elif kind == "weeks":
            months = first / spec_v2.UNIT_WEEKS_IN_MONTH
        elif kind == "days":
            months = first / spec_v2.UNIT_DAYS_IN_MONTH
        else:
            months = first
        rounded = int(months) if kind == "months" else int(round(months))
        if in_limits(spec_v2.FIELD_AGE_MONTHS, rounded):
            return rounded
    for pattern, kind in AGE_WORD_NUMBER_RULES:
        found = pattern.search(text)
        if found is None:
            continue
        count = spec_v2.NUMBER_WORDS.get(found.group(1))
        if count is None:
            continue
        if kind == "year_plus_months":
            months = spec_v2.UNIT_MONTHS_IN_YEAR + count
        elif kind == "years":
            months = count * spec_v2.UNIT_MONTHS_IN_YEAR
        else:
            months = count
        if in_limits(spec_v2.FIELD_AGE_MONTHS, months):
            return months
    return None


def mask_weight_noise(text: str) -> str:
    masked = text
    for pattern in WEIGHT_MASK_RULES:
        masked = pattern.sub(" ", masked)
    return masked


def match_weight(text: str) -> Optional[float]:
    text = mask_weight_noise(text)
    for pattern, kind in WEIGHT_RULES:
        found = pattern.search(text)
        if found is None:
            continue
        first = to_number(found.group(1))
        if first is None:
            continue
        if kind == "kg_g":
            grams = to_number(found.group(2)) or 0.0
            kilograms = first + grams / spec_v2.UNIT_GRAMS_IN_KILOGRAM
        elif kind == "grams":
            kilograms = first / spec_v2.UNIT_GRAMS_IN_KILOGRAM
        elif kind == "auto":
            kilograms = (
                first / spec_v2.UNIT_GRAMS_IN_KILOGRAM
                if first >= spec_v2.GRAMS_THRESHOLD
                else first
            )
        else:
            kilograms = first
        kilograms = round(kilograms, 3)
        if in_limits(spec_v2.FIELD_WEIGHT_KG, kilograms):
            return kilograms
    return None


def match_simple(text: str, rules, field_name: str) -> Optional[float]:
    for pattern, _kind in rules:
        found = pattern.search(text)
        if found is None:
            continue
        value = to_number(found.group(1))
        if value is None:
            continue
        if in_limits(field_name, value):
            return value
    return None


def parse_message(text: str) -> ChildProfile:
    normalized = normalize_text(text)
    values: Dict[str, Any] = {}
    age = match_age(normalized)
    if age is not None:
        values[spec_v2.FIELD_AGE_MONTHS] = age
    weight = match_weight(normalized)
    if weight is not None:
        values[spec_v2.FIELD_WEIGHT_KG] = weight
    height = match_simple(normalized, HEIGHT_RULES, spec_v2.FIELD_HEIGHT_CM)
    if height is not None:
        values[spec_v2.FIELD_HEIGHT_CM] = height
    sleep = match_simple(normalized, SLEEP_RULES, spec_v2.FIELD_SLEEP_HOURS)
    if sleep is not None:
        values[spec_v2.FIELD_SLEEP_HOURS] = sleep
    feedings = match_simple(normalized, FEEDING_RULES, spec_v2.FIELD_FEEDINGS)
    if feedings is not None:
        values[spec_v2.FIELD_FEEDINGS] = int(round(feedings))
    return ChildProfile(values=values, issues=[], supplied=bool(values))


def merge(from_message: ChildProfile, from_profile: ChildProfile) -> Tuple[ChildProfile, str]:
    values: Dict[str, Any] = dict(from_profile.values)
    values.update(from_message.values)
    merged = ChildProfile(values=values, issues=list(from_profile.issues), supplied=True)
    used_message = bool(from_message.values)
    used_profile = any(
        name not in from_message.values for name in from_profile.values
    )
    if used_message and used_profile:
        return merged, spec_v2.DATA_SOURCE_BOTH
    if used_message:
        return merged, spec_v2.DATA_SOURCE_MESSAGE
    if from_profile.values:
        return merged, spec_v2.DATA_SOURCE_PROFILE
    return merged, spec_v2.DATA_SOURCE_NONE


def prompt_block(profile: ChildProfile) -> str:
    if not profile.present:
        return ""
    lines = [spec_v2.CHILD_PROFILE_BLOCK_HEADER]
    for name in profile.names:
        lines.append(
            spec_v2.CHILD_PROFILE_LINE
            % (spec_v2.CHILD_PROFILE_TITLES[name], number_text(profile.values[name]))
        )
    lines.append(spec_v2.CHILD_PROFILE_BLOCK_TAIL)
    return "\n".join(lines)


def sleep_reference(age_months: int) -> Tuple[float, float]:
    for max_age, low, high in spec_v2.SLEEP_REFERENCE:
        if age_months <= max_age:
            return low, high
    last = spec_v2.SLEEP_REFERENCE[-1]
    return last[1], last[2]


def range_line(
    value: float, low: float, high: float, inside: str, below: str, above: str
) -> Tuple[str, bool]:
    low_text = number_text(low)
    high_text = number_text(high)
    value_text = number_text(value)
    if value < low:
        return below % (value_text, low_text, high_text), True
    if value > high:
        return above % (value_text, low_text, high_text), True
    return inside % (value_text, low_text, high_text), False


def feedings_line(count: int, age_months: int) -> str:
    if age_months <= spec_v2.FEEDING_NEWBORN_AGE_MONTHS and count < spec_v2.FEEDING_NEWBORN_LOW:
        return spec_v2.DATA_INSIGHT_FEEDINGS_LOW % (count, spec_v2.FEEDING_NEWBORN_LOW)
    if age_months <= spec_v2.FEEDING_INFANT_AGE_MONTHS and count < spec_v2.FEEDING_INFANT_LOW:
        return spec_v2.DATA_INSIGHT_FEEDINGS_LOW_INFANT % (count, spec_v2.FEEDING_INFANT_LOW)
    return spec_v2.DATA_INSIGHT_FEEDINGS_LINE % count


def compare_lines(profile: ChildProfile) -> Tuple[List[str], bool, bool]:
    age_months = profile.age_months
    if age_months is None:
        return [], False, False
    reference = spec_v2.GROWTH_REFERENCE.get(age_months)
    if reference is None:
        return [], False, False
    lines = [
        spec_v2.DATA_INSIGHT_AGE_LINE
        % ("%d %s" % (age_months, spec_v2.DATA_INSIGHT_AGE_MONTHS_SUFFIX))
    ]
    deviated = False
    weight = profile.values.get(spec_v2.FIELD_WEIGHT_KG)
    if weight is not None:
        line, out = range_line(
            weight,
            reference[spec_v2.GROWTH_WEIGHT_LOW_INDEX],
            reference[spec_v2.GROWTH_WEIGHT_HIGH_INDEX],
            spec_v2.DATA_INSIGHT_WEIGHT_IN,
            spec_v2.DATA_INSIGHT_WEIGHT_LOW,
            spec_v2.DATA_INSIGHT_WEIGHT_HIGH,
        )
        lines.append(line)
        deviated = deviated or out
    height = profile.values.get(spec_v2.FIELD_HEIGHT_CM)
    if height is not None:
        line, out = range_line(
            height,
            reference[spec_v2.GROWTH_HEIGHT_LOW_INDEX],
            reference[spec_v2.GROWTH_HEIGHT_HIGH_INDEX],
            spec_v2.DATA_INSIGHT_HEIGHT_IN,
            spec_v2.DATA_INSIGHT_HEIGHT_LOW,
            spec_v2.DATA_INSIGHT_HEIGHT_HIGH,
        )
        lines.append(line)
        deviated = deviated or out
    sleep = profile.values.get(spec_v2.FIELD_SLEEP_HOURS)
    if sleep is not None:
        sleep_low, sleep_high = sleep_reference(age_months)
        line, out = range_line(
            sleep,
            sleep_low,
            sleep_high,
            spec_v2.DATA_INSIGHT_SLEEP_IN,
            spec_v2.DATA_INSIGHT_SLEEP_LOW,
            spec_v2.DATA_INSIGHT_SLEEP_HIGH,
        )
        lines.append(line)
        deviated = deviated or out
    feedings = profile.values.get(spec_v2.FIELD_FEEDINGS)
    if feedings is not None:
        lines.append(feedings_line(int(feedings), age_months))
    notes = profile.values.get(spec_v2.FIELD_NOTES)
    if notes:
        lines.append(spec_v2.DATA_INSIGHT_NOTES_LINE % notes)
    return lines, deviated, profile.has_metrics
