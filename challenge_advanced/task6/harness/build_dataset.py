"""Сборка датасета ALVA: сырьё raw/pairs_*.jsonl -> нормализация -> чистка -> сплит.

Пишет artifacts/dataset_full.jsonl, artifacts/train.jsonl, artifacts/eval.jsonl
(только ключ messages) и results/dataset_stats.json. Код возврата 1, если примеров меньше 50.
Запуск: python3 harness/build_dataset.py
"""

import glob
import hashlib
import json
import os
import random
import re
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import score
import spec

REJECT_REASONS = (
    "bad_json",
    "empty",
    "too_short",
    "too_long",
    "dup_exact",
    "dup_near",
    "bad_bucket",
    "template_mismatch",
    "low_score",
)

_TRAILING_SPACE_RE = re.compile(r"[ \t]+$", re.MULTILINE)
_BLANK_RUN_RE = re.compile(r"\n{3,}")
_NON_WORD_RE = re.compile(r"[^\w]", re.UNICODE)


def normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _TRAILING_SPACE_RE.sub("", normalized)
    normalized = _BLANK_RUN_RE.sub("\n\n", normalized)
    return normalized.strip()


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _near_key(user: str, assistant: str) -> str:
    return _sha1(_NON_WORD_RE.sub("", (user + assistant).lower()))


def read_raw() -> Tuple[List[Dict[str, Any]], int]:
    records = []
    bad_json = 0
    paths = sorted(glob.glob(os.path.join(spec.RAW_DIR, "pairs_*.jsonl")))
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except ValueError:
                    bad_json += 1
                    continue
                if not isinstance(payload, dict):
                    bad_json += 1
                    continue
                payload["_file"] = os.path.basename(path)
                payload["_line"] = number
                records.append(payload)
    return records, bad_json


def clean(records: List[Dict[str, Any]], bad_json: int) -> Tuple[List[Dict[str, Any]], Dict[str, int], List[Dict[str, Any]]]:
    rejected = {}
    for reason in REJECT_REASONS:
        rejected[reason] = 0
    rejected["bad_json"] = bad_json
    dropped = []
    seen_exact = set()
    seen_near = set()
    kept = []

    for record in records:
        user = normalize(record.get("user", ""))
        assistant = normalize(record.get("assistant", ""))
        bucket = record.get("bucket", "")
        template = record.get("template", "")
        origin = "%s:%s" % (record.get("_file", "?"), record.get("_line", "?"))

        reason = None
        if not user or not assistant:
            reason = "empty"
        elif len(user) < spec.MIN_USER_CHARS or len(assistant) < spec.MIN_ASSISTANT_CHARS:
            reason = "too_short"
        elif len(assistant) > spec.MAX_ASSISTANT_CHARS:
            reason = "too_long"
        else:
            exact_key = _sha1(user + assistant)
            near_key = _near_key(user, assistant)
            if exact_key in seen_exact:
                reason = "dup_exact"
            elif near_key in seen_near:
                reason = "dup_near"
            elif bucket not in spec.BUCKETS:
                reason = "bad_bucket"
            elif template != spec.BUCKETS[bucket]:
                reason = "template_mismatch"
            else:
                result = score.score_example(user, assistant, template)
                if result["score"] < 1.0:
                    reason = "low_score"
                    record["_failed"] = result["failed"]

            if reason is None:
                seen_exact.add(exact_key)
                seen_near.add(near_key)

        if reason is not None:
            rejected[reason] = rejected.get(reason, 0) + 1
            dropped.append(
                {
                    "origin": origin,
                    "bucket": bucket,
                    "reason": reason,
                    "failed": record.get("_failed", []),
                }
            )
            continue

        kept.append(
            {
                "bucket": bucket,
                "template": template,
                "is_real": bool(record.get("is_real", False)),
                "source": record.get("source", ""),
                "user": user,
                "assistant": assistant,
                "origin": origin,
            }
        )

    return kept, rejected, dropped


def split_by_bucket(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    grouped = {}
    for record in records:
        grouped.setdefault(record["bucket"], []).append(record)
    train = []
    evaluation = []
    for bucket in sorted(grouped.keys()):
        items = grouped[bucket]
        size = len(items)
        eval_size = int(round(size * spec.EVAL_RATIO))
        if size >= 2 and eval_size < 1:
            eval_size = 1
        if eval_size >= size:
            eval_size = size - 1 if size > 1 else 0
        evaluation.extend(items[:eval_size])
        train.extend(items[eval_size:])
    return train, evaluation


def to_messages(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": spec.SYSTEM_PROMPT},
            {"role": "user", "content": record["user"]},
            {"role": "assistant", "content": record["assistant"]},
        ]
    }


def write_jsonl(path: str, records: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(to_messages(record), ensure_ascii=False))
            handle.write("\n")


def bucket_counts(records: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {}
    for record in records:
        counts[record["bucket"]] = counts.get(record["bucket"], 0) + 1
    return counts


def main() -> int:
    for directory in (spec.ARTIFACTS_DIR, spec.RESULTS_DIR):
        if not os.path.isdir(directory):
            os.makedirs(directory)

    raw_records, bad_json = read_raw()
    kept, rejected, dropped = clean(raw_records, bad_json)

    random.Random(spec.SPLIT_SEED).shuffle(kept)
    train, evaluation = split_by_bucket(kept)

    full_path = os.path.join(spec.ARTIFACTS_DIR, "dataset_full.jsonl")
    train_path = os.path.join(spec.ARTIFACTS_DIR, "train.jsonl")
    eval_path = os.path.join(spec.ARTIFACTS_DIR, "eval.jsonl")
    write_jsonl(full_path, kept)
    write_jsonl(train_path, train)
    write_jsonl(eval_path, evaluation)

    total_final = len(kept)
    real_count = len([record for record in kept if record["is_real"]])
    real_share = (100.0 * real_count / total_final) if total_final else 0.0
    lengths = [len(record["assistant"]) for record in kept]
    words = [len(record["assistant"].split()) for record in kept]
    avg_chars = (float(sum(lengths)) / len(lengths)) if lengths else 0.0
    avg_words = (float(sum(words)) / len(words)) if words else 0.0

    stats = {
        "raw_total": len(raw_records) + bad_json,
        "rejected_total": sum(rejected.values()),
        "rejected": rejected,
        "dropped": dropped,
        "total_final": total_final,
        "real_count": real_count,
        "real_share_pct": round(real_share, 2),
        "train_size": len(train),
        "eval_size": len(evaluation),
        "buckets": {
            "total": bucket_counts(kept),
            "train": bucket_counts(train),
            "eval": bucket_counts(evaluation),
        },
        "assistant_avg_chars": round(avg_chars, 1),
        "assistant_avg_words": round(avg_words, 1),
        "seed": spec.SPLIT_SEED,
        "eval_ratio": spec.EVAL_RATIO,
        "files": {
            "dataset_full": full_path,
            "train": train_path,
            "eval": eval_path,
        },
    }
    stats_path = os.path.join(spec.RESULTS_DIR, "dataset_stats.json")
    with open(stats_path, "w", encoding="utf-8") as handle:
        json.dump(stats, handle, ensure_ascii=False, indent=2)

    print("сырьё: %d строк" % stats["raw_total"])
    print("отброшено: %d" % stats["rejected_total"])
    for reason in REJECT_REASONS:
        print("  %-18s %d" % (reason, rejected.get(reason, 0)))
    print("итог: %d (train %d / eval %d)" % (total_final, len(train), len(evaluation)))
    print("реальных: %d (%.1f%%)" % (real_count, real_share))
    print("средняя длина ответа: %.1f символов, %.1f слов" % (avg_chars, avg_words))
    print("")
    print("%-16s %-7s %-7s %s" % ("bucket", "total", "train", "eval"))
    print("-" * 44)
    for bucket in sorted(spec.BUCKETS.keys()):
        print(
            "%-16s %-7d %-7d %d"
            % (
                bucket,
                stats["buckets"]["total"].get(bucket, 0),
                stats["buckets"]["train"].get(bucket, 0),
                stats["buckets"]["eval"].get(bucket, 0),
            )
        )
    print("-" * 44)
    print("статистика: %s" % stats_path)

    if total_final < spec.MIN_DATASET_SIZE:
        print("")
        print(
            "ВНИМАНИЕ: ПРИМЕРОВ %d, ТРЕБУЕТСЯ НЕ МЕНЬШЕ %d. ДАТАСЕТ НЕ ГОТОВ."
            % (total_final, spec.MIN_DATASET_SIZE)
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
