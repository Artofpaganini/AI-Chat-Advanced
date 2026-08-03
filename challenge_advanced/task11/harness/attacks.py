"""Загрузка и фильтрация набора атак из data/attacks.jsonl.

Формат записи: id, technique (T1-T5), class (direct/indirect/jailbreak), target
(jarvis/alva/bank/all), text, expected_detector, source, split (dev/holdout).
"""

import json
import os
from typing import Any, Dict, List

import spec11

REQUIRED_FIELDS = ("id", "technique", "class", "target", "text", "expected_detector", "source", "split")


class AttacksError(Exception):
    pass


def load_attacks(path: str = spec11.ATTACKS_PATH) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        raise AttacksError("файл атак не найден: %s" % path)
    attacks: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except ValueError as parse_error:
                raise AttacksError("%s:%d не парсится как JSON: %s" % (path, line_number, parse_error))
            validate_attack(record, path, line_number)
            attacks.append(record)
    check_unique_ids(attacks, path)
    return attacks


def validate_attack(record: Dict[str, Any], path: str, line_number: int) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise AttacksError("%s:%d не хватает полей %s" % (path, line_number, missing))
    if record["technique"] not in spec11.TECHNIQUES:
        raise AttacksError("%s:%d неизвестная техника %r" % (path, line_number, record["technique"]))
    if record["class"] not in spec11.CLASSES:
        raise AttacksError("%s:%d неизвестный класс %r" % (path, line_number, record["class"]))
    if record["target"] not in spec11.TARGETS + (spec11.TARGET_ALL,):
        raise AttacksError("%s:%d неизвестная мишень %r" % (path, line_number, record["target"]))
    if record["split"] not in spec11.SPLITS:
        raise AttacksError("%s:%d неизвестный split %r" % (path, line_number, record["split"]))
    if record["expected_detector"] not in spec11.DETECTOR_CODES:
        raise AttacksError(
            "%s:%d неизвестный expected_detector %r" % (path, line_number, record["expected_detector"])
        )
    if not str(record["text"]).strip():
        raise AttacksError("%s:%d пустой text" % (path, line_number))
    family = record.get("family", spec11.FAMILY_OWN)
    if family not in spec11.FAMILIES:
        raise AttacksError("%s:%d неизвестный family %r" % (path, line_number, family))
    mode = record.get("mode", spec11.MODE_SINGLE)
    if mode == spec11.MODE_PIPELINE:
        validate_pipeline_attack(record, path, line_number)
    elif mode != spec11.MODE_SINGLE:
        raise AttacksError("%s:%d неизвестный mode %r" % (path, line_number, mode))


def validate_pipeline_attack(record: Dict[str, Any], path: str, line_number: int) -> None:
    if record["target"] != spec11.TARGET_ALVA:
        raise AttacksError("%s:%d mode=pipeline применим только к target=alva" % (path, line_number))
    check = record.get("pipeline_check")
    if check not in (spec11.PIPELINE_CHECK_FIELD_SPOOF, spec11.PIPELINE_CHECK_ROUTE_FLIP):
        raise AttacksError("%s:%d неизвестный pipeline_check %r" % (path, line_number, check))
    if check == spec11.PIPELINE_CHECK_ROUTE_FLIP and not record.get("pipeline_expected_route"):
        raise AttacksError("%s:%d route_flip требует pipeline_expected_route" % (path, line_number))


def check_unique_ids(attacks: List[Dict[str, Any]], path: str) -> None:
    seen: Dict[str, int] = {}
    for record in attacks:
        attack_id = record["id"]
        if attack_id in seen:
            raise AttacksError("%s: дублирующийся id %r" % (path, attack_id))
        seen[attack_id] = 1


def targets_of(record: Dict[str, Any]) -> List[str]:
    if record["target"] == spec11.TARGET_ALL:
        return list(spec11.TARGETS)
    return [record["target"]]


def matches_target(record: Dict[str, Any], target_filter: str) -> bool:
    if target_filter == spec11.TARGET_ALL:
        return True
    return target_filter in targets_of(record)


def filter_attacks(
    attacks: List[Dict[str, Any]],
    target: str = spec11.TARGET_ALL,
    split: str = spec11.TARGET_ALL,
    ids: Any = None,
) -> List[Dict[str, Any]]:
    filtered = [record for record in attacks if matches_target(record, target)]
    if split != spec11.TARGET_ALL:
        filtered = [record for record in filtered if record["split"] == split]
    if ids:
        wanted = set(ids)
        filtered = [record for record in filtered if record["id"] in wanted]
    return filtered


def expand_by_target(attacks: List[Dict[str, Any]], target_filter: str) -> List[Dict[str, Any]]:
    """Разворачивает записи с target=all в отдельный кейс на каждую реальную мишень."""
    expanded: List[Dict[str, Any]] = []
    for record in attacks:
        for target in targets_of(record):
            if target_filter != spec11.TARGET_ALL and target != target_filter:
                continue
            case = dict(record)
            case["target"] = target
            case["attack_id"] = record["id"]
            case["family"] = record.get("family", spec11.FAMILY_OWN)
            expanded.append(case)
    return expanded


def split_counts(attacks: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {split: 0 for split in spec11.SPLITS}
    for record in attacks:
        counts[record["split"]] = counts.get(record["split"], 0) + 1
    return counts
