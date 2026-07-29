#!/usr/bin/env python3
"""Выбор LoRA-чекпоинта по поведению, а не по validation loss.

Урок task6: минимум val loss не совпал с лучшим поведением модели. Здесь каждый
чекпоинт прогоняется по отложенному valid-сплиту триажа и оценивается теми же
проверками, что и боевой ответ - harness/guards.check_reply со SPEC-кодами.

Тестовый набор data/cases.jsonl не читается: замер на нём делает отдельный прогон.

Запуск: python3 harness/pick_triage_checkpoint.py --out raw/checkpoint_pick.json
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

import guards
import spec7

TASK_ROOT = HARNESS_DIR.parent
DEFAULT_VALID = TASK_ROOT / "data" / "mlx_triage" / "valid.jsonl"
DEFAULT_ADAPTERS = Path("/Users/Victor/models/alva-triage-qwen-lora")
BASE_MODEL = "mlx-community/Qwen3-1.7B-4bit"
MAX_TOKENS = 400
THINK_PATTERN = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL)


def strip_think(raw_text: str) -> tuple[str, bool]:
    stripped = THINK_PATTERN.sub("", raw_text, count=1)
    return stripped, stripped != raw_text


def load_valid(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            messages = json.loads(line)["messages"]
            gold = json.loads(messages[-1]["content"])
            rows.append(
                {
                    "system": messages[0]["content"],
                    "user": messages[1]["content"],
                    "gold_route": gold["route"],
                }
            )
    return rows


def build_adapter_dirs(adapters_dir: Path, work_dir: Path) -> list[tuple[str, Path]]:
    config = adapters_dir / "adapter_config.json"
    if not config.exists():
        sys.exit(f"нет {config}")
    entries: list[tuple[str, Path]] = []
    for weights in sorted(adapters_dir.glob("[0-9]*_adapters.safetensors")):
        label = str(int(weights.name.split("_", 1)[0]))
        target = work_dir / f"iter{label}"
        target.mkdir(parents=True, exist_ok=True)
        link = target / "adapters.safetensors"
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(weights)
        copy = target / "adapter_config.json"
        copy.write_text(config.read_text(encoding="utf-8"), encoding="utf-8")
        entries.append((label, target))
    return entries


def score_one(model, tokenizer, rows: list[dict], sampler) -> dict:
    from mlx_lm import generate

    correct = 0
    missed_emergency = 0
    over_escalated = 0
    valid_json = 0
    hard_violations = 0
    fenced = 0
    think_blocks = 0
    codes: Counter = Counter()
    confusion: Counter = Counter()
    per_case = []

    for row in rows:
        messages = [
            {"role": "system", "content": row["system"]},
            {"role": "user", "content": row["user"]},
        ]
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        raw = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=MAX_TOKENS,
            sampler=sampler,
            verbose=False,
        )
        body, had_think = strip_think(raw)
        if had_think:
            think_blocks += 1
        result = guards.check_reply(body)
        if result.parsed is not None:
            valid_json += 1
        if guards.has_hard_violation(result.violations):
            hard_violations += 1
        if spec7.W_FENCED in result.violations:
            fenced += 1
        for code in result.violations:
            codes[code] += 1

        predicted = result.parsed.get("route") if result.parsed else None
        gold = row["gold_route"]
        confusion[(gold, predicted)] += 1
        if predicted == gold:
            correct += 1
        if gold == spec7.ROUTE_EMERGENCY and predicted != spec7.ROUTE_EMERGENCY:
            missed_emergency += 1
        if gold != spec7.ROUTE_EMERGENCY and predicted == spec7.ROUTE_EMERGENCY:
            over_escalated += 1
        per_case.append({"gold": gold, "predicted": predicted, "violations": result.violations})

    total = len(rows)
    return {
        "n": total,
        "accuracy": round(correct / total, 4),
        "missed_emergency": missed_emergency,
        "over_escalated": over_escalated,
        "valid_json": valid_json,
        "valid_json_rate": round(valid_json / total, 4),
        "hard_violations": hard_violations,
        "fenced": fenced,
        "think_blocks": think_blocks,
        "codes": dict(codes),
        "confusion": {f"{gold}->{pred}": count for (gold, pred), count in confusion.items()},
        "per_case": per_case,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Выбор чекпоинта по поведению на отложенном сплите")
    parser.add_argument("--valid", type=Path, default=DEFAULT_VALID)
    parser.add_argument("--adapters", type=Path, default=DEFAULT_ADAPTERS)
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--out", type=Path, default=TASK_ROOT / "raw" / "checkpoint_pick.json")
    parser.add_argument("--work-dir", type=Path, default=Path(os.environ.get("TMPDIR", "/tmp")) / "triage_ckpt")
    parser.add_argument("--include-base", action="store_true", help="добавить точку без адаптера")
    args = parser.parse_args()

    from mlx_lm.sample_utils import make_sampler
    from mlx_lm.utils import load

    rows = load_valid(args.valid)
    sampler = make_sampler(temp=0.0)
    args.work_dir.mkdir(parents=True, exist_ok=True)

    targets: list[tuple[str, Path | None]] = []
    if args.include_base:
        targets.append(("base", None))
    targets.extend(build_adapter_dirs(args.adapters, args.work_dir))

    report = {"model": args.model, "valid": str(args.valid), "n": len(rows), "checkpoints": {}}
    for label, adapter_dir in targets:
        started = time.time()
        model, tokenizer = load(
            args.model,
            adapter_path=str(adapter_dir) if adapter_dir else None,
        )
        scored = score_one(model, tokenizer, rows, sampler)
        scored["seconds"] = round(time.time() - started, 1)
        scored["adapter"] = str(adapter_dir) if adapter_dir else None
        report["checkpoints"][label] = scored
        print(
            f"{label:>6}  acc {scored['accuracy']:.4f}  "
            f"missed_EMERG {scored['missed_emergency']}  "
            f"over_esc {scored['over_escalated']}  "
            f"json {scored['valid_json']}/{scored['n']}  "
            f"hard_viol {scored['hard_violations']}  "
            f"{scored['seconds']}s",
            flush=True,
        )
        del model, tokenizer

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nотчёт: {args.out}")


if __name__ == "__main__":
    main()
