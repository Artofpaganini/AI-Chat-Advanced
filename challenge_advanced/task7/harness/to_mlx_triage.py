#!/usr/bin/env python3
"""Готовит датасет триажа для mlx_lm.lora.

Читает data/train_triage.jsonl, делит стратифицированно по маршруту на train и valid
и раскладывает в data/mlx_triage/ в нативном chat-формате mlx-lm: {"messages": [...]}.

Формат проверен по mlx_lm/tuner/datasets.py версии 0.31.3: create_dataset смотрит на
ключ "messages" (chat_feature) и берёт ChatDataset. Строки на входе уже в этом виде,
конвертер их не переписывает, только раскладывает и проверяет.

Запуск: python3 harness/to_mlx_triage.py
"""

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

SEED = 1337
VALID_RATIO = 0.2
ROUTES = ("EMERGENCY", "DOCTOR_SOON", "SELF_CARE", "OFF_TOPIC")

TASK_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = TASK_ROOT / "data" / "train_triage.jsonl"
DEFAULT_OUT = TASK_ROOT / "data" / "mlx_triage"


def read_rows(src: Path) -> list[dict]:
    rows = []
    with src.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                sys.exit(f"{src}:{line_no} не разбирается как JSON: {error}")
            messages = row.get("messages")
            if not isinstance(messages, list) or len(messages) < 2:
                sys.exit(f"{src}:{line_no} нет поля messages или в нём меньше двух сообщений")
            if messages[-1].get("role") != "assistant":
                sys.exit(f"{src}:{line_no} последнее сообщение не от assistant")
            rows.append(row)
    if not rows:
        sys.exit(f"{src} пустой")
    return rows


def route_of(row: dict, index: int) -> str:
    raw = row["messages"][-1]["content"]
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError as error:
        sys.exit(f"строка {index}: ответ ассистента не JSON: {error}")
    route = answer.get("route")
    if route not in ROUTES:
        sys.exit(f"строка {index}: маршрут {route!r} вне списка {ROUTES}")
    return route


def split(rows: list[dict], valid_ratio: float, seed: int) -> tuple[list[dict], list[dict]]:
    by_route: dict[str, list[dict]] = defaultdict(list)
    for index, row in enumerate(rows, start=1):
        by_route[route_of(row, index)].append(row)

    rng = random.Random(seed)
    train: list[dict] = []
    valid: list[dict] = []
    for route in ROUTES:
        bucket = list(by_route.get(route, []))
        rng.shuffle(bucket)
        take = round(len(bucket) * valid_ratio)
        valid.extend(bucket[:take])
        train.extend(bucket[take:])

    rng.shuffle(train)
    rng.shuffle(valid)
    return train, valid


def write_jsonl(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps({"messages": row["messages"]}, ensure_ascii=False) + "\n")


def report(name: str, rows: list[dict]) -> None:
    counts = Counter(route_of(row, index) for index, row in enumerate(rows, start=1))
    total = len(rows)
    print(f"{name}: {total} примеров")
    for route in ROUTES:
        count = counts.get(route, 0)
        share = count / total * 100 if total else 0.0
        print(f"  {route:<12} {count:>4}  {share:5.1f}%")


def main() -> None:
    parser = argparse.ArgumentParser(description="Конвертация датасета триажа под mlx_lm.lora")
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--valid-ratio", type=float, default=VALID_RATIO)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    rows = read_rows(args.src)
    train, valid = split(rows, args.valid_ratio, args.seed)

    args.out.mkdir(parents=True, exist_ok=True)
    write_jsonl(train, args.out / "train.jsonl")
    write_jsonl(valid, args.out / "valid.jsonl")

    print(f"источник: {args.src}  строк: {len(rows)}")
    print(f"seed: {args.seed}  доля valid: {args.valid_ratio}")
    print(f"каталог: {args.out}")
    print()
    report("train", train)
    print()
    report("valid", valid)


if __name__ == "__main__":
    main()
