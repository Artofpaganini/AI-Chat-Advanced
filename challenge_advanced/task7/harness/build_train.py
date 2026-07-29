"""Сборка обучающего набора триажа в формате чата для mlx-lm.

Системный промпт берётся ОДНОЙ константой из spec7.py (TRIAGE_SYSTEM_PROMPT),
чтобы обучение и инференс не разъехались.
Выход: task7/data/train_triage.jsonl, по одному примеру в строке.
Разметка покрытия (band / style / structure / tone) в обучающий файл не попадает,
её читает только verify_train.py.
"""

import json
import os
import sys

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HARNESS_DIR)

if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import spec7

from cases_doctor_soon import DOCTOR_SOON_CASES
from cases_emergency import EMERGENCY_CASES
from cases_off_topic import OFF_TOPIC_CASES
from cases_self_care import SELF_CARE_CASES

OUTPUT_PATH = os.path.join(TASK_DIR, "data", "train_triage.jsonl")

TARGET_COUNTS = {
    spec7.ROUTE_EMERGENCY: 90,
    spec7.ROUTE_DOCTOR_SOON: 65,
    spec7.ROUTE_SELF_CARE: 80,
    spec7.ROUTE_OFF_TOPIC: 25,
}

ROUTE_GROUPS = (
    (spec7.ROUTE_EMERGENCY, EMERGENCY_CASES),
    (spec7.ROUTE_DOCTOR_SOON, DOCTOR_SOON_CASES),
    (spec7.ROUTE_SELF_CARE, SELF_CARE_CASES),
    (spec7.ROUTE_OFF_TOPIC, OFF_TOPIC_CASES),
)


def build_reply(route, case):
    return {
        "route": route,
        "red_flags": list(case.get("red_flags", [])),
        "age_months": case.get("age_months"),
        "confidence": case["confidence"],
        "reason": case["reason"],
    }


def build_example(route, case):
    reply = build_reply(route, case)
    return {
        "messages": [
            {"role": "system", "content": spec7.TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": case["text"]},
            {"role": "assistant", "content": json.dumps(reply, ensure_ascii=False)},
        ]
    }


def collect():
    examples = []
    for route, cases in ROUTE_GROUPS:
        expected = TARGET_COUNTS[route]
        if len(cases) != expected:
            raise SystemExit(f"{route}: заказано {expected}, в файле {len(cases)}")
        for case in cases:
            examples.append(build_example(route, case))
    return examples


def main():
    examples = collect()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")
    print(f"written {len(examples)} -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
