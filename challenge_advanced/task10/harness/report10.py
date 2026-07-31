"""Пересчёт метрик из raw/ и проверка гейта из SPEC.md раздел 10.

Ни одно число в REPORT.md не берётся из головы: всё считается здесь по сырью.
Код возврата 1, если гейт не пройден.

Запуск: python3 harness/report10.py
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import micro_model
import spec10

LABEL_COLUMN_WIDTH = 26


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def percentile(values: Sequence[float], rank: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = int(round((rank / 100.0) * len(ordered) + 0.5)) - 1
    position = max(0, min(position, len(ordered) - 1))
    return float(ordered[position])


def mean_of(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def is_evaluable(record: Dict[str, Any]) -> bool:
    return record.get("expected_route") in spec10.LABELS


def run_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    evaluable = [record for record in records if is_evaluable(record)]
    hits = sum(
        1 for record in evaluable if record.get("final_route") == record.get("expected_route")
    )
    missed_emergency = sum(
        1
        for record in evaluable
        if record.get("expected_route") == spec10.LABEL_EMERGENCY
        and record.get("final_route") != spec10.LABEL_EMERGENCY
    )
    false_emergency = sum(
        1
        for record in evaluable
        if record.get("expected_route") != spec10.LABEL_EMERGENCY
        and record.get("final_route") == spec10.LABEL_EMERGENCY
    )
    micro_answers = sum(
        1 for record in records if record.get("micro") and not record.get("escalated")
    )
    fallback_count = sum(1 for record in records if record.get("llm"))
    llm_calls = sum(int(record.get("llm_calls") or 0) for record in records)
    cost = sum(float(record.get("cost_usd") or 0.0) for record in records)
    latencies = [float(record.get("latency_ms") or 0) for record in records]
    micro_latencies = [
        float(record["micro"]["latency_ms"]) for record in records if record.get("micro")
    ]
    errors = [record for record in records if record.get("error")]

    by_group: Dict[str, Any] = {}
    for group in spec10.GROUPS:
        subset = [record for record in evaluable if record.get("group") == group]
        group_hits = sum(
            1 for record in subset if record.get("final_route") == record.get("expected_route")
        )
        by_group[group] = {
            "cases": len(subset),
            "hits": group_hits,
            "accuracy": round(group_hits / len(subset), 4) if subset else 0.0,
            "escalated": sum(1 for record in subset if record.get("escalated")),
        }

    return {
        "cases": len(records),
        "evaluable": len(evaluable),
        "hits": hits,
        "accuracy": round(hits / len(evaluable), 4) if evaluable else 0.0,
        "missed_emergency": missed_emergency,
        "false_emergency": false_emergency,
        "handled_by_micro": micro_answers,
        "fallback_count": fallback_count,
        "llm_calls": llm_calls,
        "cost_usd": round(cost, 8),
        "latency_mean_ms": round(mean_of(latencies), 1),
        "latency_p50_ms": round(percentile(latencies, spec10.PERCENTILE_P50), 1),
        "latency_p95_ms": round(percentile(latencies, spec10.PERCENTILE_P95), 1),
        "micro_latency_mean_ms": round(mean_of(micro_latencies), 4),
        "micro_latency_p50_ms": round(percentile(micro_latencies, spec10.PERCENTILE_P50), 4),
        "errors": len(errors),
        "by_group": by_group,
    }


def spread_of(values: Sequence[float]) -> Dict[str, Any]:
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "mean": round(mean_of(values), 4),
    }


def aggregate(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    accuracies = [run["metrics"]["accuracy"] for run in runs]
    return {
        "repeats": len(runs),
        "accuracy": spread_of(accuracies),
        "missed_emergency_worst": max(run["metrics"]["missed_emergency"] for run in runs),
        "missed_emergency_best": min(run["metrics"]["missed_emergency"] for run in runs),
        "false_emergency_worst": max(run["metrics"]["false_emergency"] for run in runs),
        "handled_by_micro": spread_of([run["metrics"]["handled_by_micro"] for run in runs]),
        "fallback_count": spread_of([run["metrics"]["fallback_count"] for run in runs]),
        "llm_calls_total": sum(run["metrics"]["llm_calls"] for run in runs),
        "llm_calls_per_run": spread_of([run["metrics"]["llm_calls"] for run in runs]),
        "cost_usd_total": round(sum(run["metrics"]["cost_usd"] for run in runs), 8),
        "cost_usd_per_run": spread_of([run["metrics"]["cost_usd"] for run in runs]),
        "latency_mean_ms": spread_of([run["metrics"]["latency_mean_ms"] for run in runs]),
        "latency_p50_ms": spread_of([run["metrics"]["latency_p50_ms"] for run in runs]),
        "latency_p95_ms": spread_of([run["metrics"]["latency_p95_ms"] for run in runs]),
        "micro_latency_p50_ms": spread_of(
            [run["metrics"]["micro_latency_p50_ms"] for run in runs]
        ),
        "errors_total": sum(run["metrics"]["errors"] for run in runs),
        "accuracy_by_group": {
            group: spread_of([run["metrics"]["by_group"][group]["accuracy"] for run in runs])
            for group in spec10.GROUPS
        },
    }


def collect_runs(raw_dir: str) -> Dict[str, List[Dict[str, Any]]]:
    found: Dict[str, List[Dict[str, Any]]] = {mode: [] for mode in spec10.MODES}
    if not os.path.isdir(raw_dir):
        return found
    for name in sorted(os.listdir(raw_dir)):
        if not name.startswith(spec10.RAW_FILE_PREFIX):
            continue
        if not name.endswith(spec10.RAW_FILE_EXTENSION):
            continue
        path = os.path.join(raw_dir, name)
        records = read_jsonl(path)
        if not records:
            continue
        mode = records[0].get("mode")
        if mode not in found:
            continue
        found[mode].append(
            {
                "file": name,
                "repeat": int(records[0].get("repeat") or 1),
                "metrics": run_metrics(records),
            }
        )
    for mode in found:
        found[mode].sort(key=lambda run: run["repeat"])
    return found


def deterministic_check(raw_dir: str, mode: str) -> Dict[str, Any]:
    """only_micro обязан повторяться до знака. Расхождение - дефект харнесса, а не шум модели."""
    signatures: List[str] = []
    if os.path.isdir(raw_dir):
        for name in sorted(os.listdir(raw_dir)):
            if not name.startswith(spec10.RAW_FILE_PREFIX + mode):
                continue
            records = read_jsonl(os.path.join(raw_dir, name))
            if not records or records[0].get("mode") != mode:
                continue
            signature = json.dumps(
                [
                    [record.get("case_id"), record.get("final_route"), record["micro"]["probs"]]
                    for record in records
                    if record.get("micro")
                ],
                ensure_ascii=False,
                sort_keys=True,
            )
            signatures.append(signature)
    return {
        "runs": len(signatures),
        "identical": len(set(signatures)) <= 1 if signatures else False,
    }


def parity_check(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {"exists": False, "count": 0, "complete": False, "reason": "файла нет"}
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    entries = document.get("entries") or []
    complete = len(entries) == spec10.EXPECTED_CASES and all(
        isinstance(entry.get("probs"), list) and len(entry["probs"]) == len(spec10.LABELS)
        for entry in entries
    )
    return {
        "exists": True,
        "count": len(entries),
        "expected": spec10.EXPECTED_CASES,
        "complete": complete,
        "tolerance": document.get("tolerance"),
    }


def model_check(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {"exists": False, "bytes": 0, "kb": 0.0, "features": 0, "within_budget": False}
    size = os.path.getsize(path)
    try:
        model = micro_model.load_model(path)
    except micro_model.InvalidWeightsError as invariant_error:
        return {
            "exists": True,
            "bytes": size,
            "kb": round(size / 1024.0, 1),
            "features": 0,
            "invariant_passed": False,
            "invariant_error": str(invariant_error),
            "within_budget": False,
        }
    return {
        "exists": True,
        "invariant_passed": True,
        "bytes": size,
        "kb": round(size / 1024.0, 1),
        "limit_kb": round(spec10.MAX_MODEL_BYTES / 1024.0, 1),
        "features": model.vocabulary.size(),
        "weight_rows": len(model.weights),
        "confident_min_prob": model.confident_min_prob,
        "confident_min_margin": model.confident_min_margin,
        "always_escalate_labels": list(model.always_escalate_labels),
        "within_budget": size <= spec10.MAX_MODEL_BYTES,
    }


def files_of_mode(raw_dir: str, mode: str) -> List[Tuple[str, List[Dict[str, Any]]]]:
    found: List[Tuple[str, List[Dict[str, Any]]]] = []
    if not os.path.isdir(raw_dir):
        return found
    for name in sorted(os.listdir(raw_dir)):
        if not name.startswith(spec10.RAW_FILE_PREFIX):
            continue
        if not name.endswith(spec10.RAW_FILE_EXTENSION):
            continue
        records = read_jsonl(os.path.join(raw_dir, name))
        if records and records[0].get("mode") == mode:
            found.append((name, records))
    return found


def escalation_breakdown(raw_dir: str, mode: str) -> Dict[str, Any]:
    """Что LLM сделала с ответом micro-model: подтвердила, понизила или подняла тяжесть."""
    counts = {
        "runs": 0,
        "stayed": 0,
        "escalated": 0,
        "always_escalate": 0,
        "low_confidence": 0,
        "llm_confirmed": 0,
        "llm_lowered": 0,
        "llm_raised": 0,
        "llm_no_route": 0,
        "final_differs_from_micro": 0,
    }
    for _, records in files_of_mode(raw_dir, mode):
        counts["runs"] += 1
        for record in records:
            block = record.get("micro")
            if not block:
                continue
            if not record.get("escalated"):
                counts["stayed"] += 1
                continue
            counts["escalated"] += 1
            micro_label = block.get("label")
            if micro_label == spec10.LABEL_EMERGENCY:
                counts["always_escalate"] += 1
            else:
                counts["low_confidence"] += 1
            llm_route = (record.get("llm") or {}).get("route")
            if llm_route is None:
                counts["llm_no_route"] += 1
            elif severity_of(llm_route) > severity_of(micro_label):
                counts["llm_raised"] += 1
            elif severity_of(llm_route) < severity_of(micro_label):
                counts["llm_lowered"] += 1
            else:
                counts["llm_confirmed"] += 1
            if record.get("final_route") != micro_label:
                counts["final_differs_from_micro"] += 1
    return counts


def emergency_recall(raw_dir: str, mode: str, use_micro_answer: bool = False) -> Dict[str, Any]:
    """Сколько золотых EMERGENCY поймал уровень. use_micro_answer смотрит на ответ micro внутри каскада."""
    gold = 0
    caught = 0
    runs = 0
    for _, records in files_of_mode(raw_dir, mode):
        runs += 1
        gold = 0
        caught = 0
        for record in records:
            if record.get("expected_route") != spec10.LABEL_EMERGENCY:
                continue
            gold += 1
            if use_micro_answer:
                answer = (record.get("micro") or {}).get("label")
            else:
                answer = record.get("final_route")
            if answer == spec10.LABEL_EMERGENCY:
                caught += 1
    return {"gold": gold, "caught": caught, "runs": runs}


def compare_modes(raw_dir: str, left: str, right: str) -> Dict[str, Any]:
    """Совпали ли два режима маршрут в маршрут и сколько вызовов LLM при этом ушло впустую."""
    left_files = files_of_mode(raw_dir, left)
    right_files = files_of_mode(raw_dir, right)
    if not left_files or not right_files:
        return {"comparable": False}
    right_routes = {
        record.get("case_id"): record.get("final_route") for record in right_files[0][1]
    }
    mismatches: List[Dict[str, Any]] = []
    wasted_calls = 0
    total_calls = 0
    for name, records in left_files:
        for record in records:
            total_calls += int(record.get("llm_calls") or 0)
            expected = right_routes.get(record.get("case_id"))
            if record.get("final_route") != expected:
                mismatches.append(
                    {
                        "file": name,
                        "case_id": record.get("case_id"),
                        left: record.get("final_route"),
                        right: expected,
                    }
                )
            elif record.get("escalated"):
                wasted_calls += int(record.get("llm_calls") or 0)
    return {
        "comparable": True,
        "left": left,
        "right": right,
        "identical": not mismatches,
        "mismatches": mismatches,
        "llm_calls_total": total_calls,
        "llm_calls_that_changed_nothing": wasted_calls,
    }


def severity_of(route: Optional[str]) -> int:
    return spec10.SEVERITY.get(route or "", -1)


def rewrite_cascade(
    records: List[Dict[str, Any]], variant: str, min_prob: float, min_margin: float
) -> List[Dict[str, Any]]:
    """Пересбор итога каскада по другому правилу, из уже собранного сырья.

    Ни одного нового вызова модели: и ответ micro-model, и ответ LLM уже лежат в записи.
    """
    rebuilt: List[Dict[str, Any]] = []
    for record in records:
        block = record.get("micro")
        copy = dict(record)
        if not block:
            rebuilt.append(copy)
            continue
        micro_label = block.get("label")
        if variant == spec10.POSTHOC_SEVERITY_MAX:
            if record.get("escalated") and severity_of(micro_label) > severity_of(
                record.get("final_route")
            ):
                copy["final_route"] = micro_label
        elif variant == spec10.POSTHOC_NO_FORCE_ESCALATE:
            confident = (
                float(block.get("prob") or 0.0) >= min_prob
                and float(block.get("margin") or 0.0) >= min_margin
            )
            if confident:
                copy["final_route"] = micro_label
                copy["escalated"] = False
                copy["llm_calls"] = 0
                copy["cost_usd"] = 0.0
                copy["llm"] = None
        rebuilt.append(copy)
    return rebuilt


def posthoc_variants(raw_dir: str, model: Dict[str, Any]) -> Dict[str, Any]:
    min_prob = float(model.get("confident_min_prob") or 0.0)
    min_margin = float(model.get("confident_min_margin") or 0.0)
    files = files_of_mode(raw_dir, spec10.MODE_CASCADE)
    output: Dict[str, Any] = {}
    for variant in spec10.POSTHOC_VARIANTS:
        runs = [
            {
                "file": name,
                "repeat": int(records[0].get("repeat") or 1),
                "metrics": run_metrics(
                    rewrite_cascade(records, variant, min_prob, min_margin)
                ),
            }
            for name, records in files
        ]
        if runs:
            output[variant] = aggregate(runs)
    return output


def evaluate_gate(
    summary: Dict[str, Any],
    parity: Dict[str, Any],
    model: Dict[str, Any],
    mode: str = spec10.MODE_CASCADE,
) -> Tuple[Dict[str, Any], bool]:
    cascade = summary.get(mode)
    only_llm = summary.get(spec10.MODE_ONLY_LLM)
    only_micro = summary.get(spec10.MODE_ONLY_MICRO)
    checks: Dict[str, Any] = {}

    if cascade and only_llm:
        checks[spec10.GATE_EMERGENCY] = {
            "passed": cascade["missed_emergency_worst"] <= only_llm["missed_emergency_worst"],
            "cascade": cascade["missed_emergency_worst"],
            "only_llm": only_llm["missed_emergency_worst"],
        }
        checks[spec10.GATE_CALLS] = {
            "passed": cascade["llm_calls_total"] < only_llm["llm_calls_total"],
            "cascade": cascade["llm_calls_total"],
            "only_llm": only_llm["llm_calls_total"],
        }
    else:
        checks[spec10.GATE_EMERGENCY] = {"passed": False, "reason": "нет прогонов для сравнения"}
        checks[spec10.GATE_CALLS] = {"passed": False, "reason": "нет прогонов для сравнения"}

    if cascade and only_micro:
        checks[spec10.GATE_ACCURACY] = {
            "passed": cascade["accuracy"]["min"] >= only_micro["accuracy"]["min"],
            "cascade": cascade["accuracy"]["min"],
            "only_micro": only_micro["accuracy"]["min"],
        }
    else:
        checks[spec10.GATE_ACCURACY] = {"passed": False, "reason": "нет прогонов для сравнения"}

    checks[spec10.GATE_PARITY] = {
        "passed": bool(parity.get("complete")),
        "count": parity.get("count"),
        "expected": spec10.EXPECTED_CASES,
    }
    checks[spec10.GATE_SIZE] = {
        "passed": bool(model.get("within_budget")),
        "kb": model.get("kb"),
        "limit_kb": model.get("limit_kb"),
    }
    passed = all(entry.get("passed") for entry in checks.values())
    return checks, passed


def print_report(report: Dict[str, Any]) -> None:
    summary = report["summary"]
    modes = [mode for mode in spec10.MODES if mode in summary]
    print("Режимы, %d повторов каждый" % spec10.DEFAULT_REPEATS)
    print(
        "  %-*s %s"
        % (LABEL_COLUMN_WIDTH, "метрика", " ".join("%-19s" % mode for mode in modes))
    )

    def cell(mode: str, getter) -> str:
        block = summary.get(mode)
        if not block:
            return "-"
        return getter(block)

    def line(title: str, getter) -> None:
        print(
            "  %-*s %s"
            % (
                LABEL_COLUMN_WIDTH,
                title,
                " ".join("%-19s" % cell(mode, getter) for mode in modes),
            )
        )

    rows = [
        ("точность min..max", lambda block: "%.4f .. %.4f" % (block["accuracy"]["min"], block["accuracy"]["max"])),
        ("пропущено EMERGENCY", lambda block: str(block["missed_emergency_worst"])),
        ("ложных тревог", lambda block: str(block["false_emergency_worst"])),
        ("закрыто micro-model", lambda block: "%.1f" % block["handled_by_micro"]["mean"]),
        ("ушло в fallback", lambda block: "%.1f" % block["fallback_count"]["mean"]),
        ("вызовов LLM всего", lambda block: str(block["llm_calls_total"])),
        ("стоимость USD всего", lambda block: "%.6f" % block["cost_usd_total"]),
        ("средняя задержка мс", lambda block: "%.1f" % block["latency_mean_ms"]["mean"]),
        ("p50 задержка мс", lambda block: "%.1f" % block["latency_p50_ms"]["mean"]),
        ("p95 задержка мс", lambda block: "%.1f" % block["latency_p95_ms"]["mean"]),
        ("ошибок", lambda block: str(block["errors_total"])),
    ]
    for title, getter in rows:
        line(title, getter)
    print("")
    print("Точность по группам, среднее по повторам")
    for group in spec10.GROUPS:
        line(group, lambda block, name=group: "%.4f" % block["accuracy_by_group"][name]["mean"])

    print("")
    print("Что LLM сделала с ответом micro-model, по каскадам")
    for mode in spec10.CASCADE_MODES:
        block = (report.get("escalation") or {}).get(mode)
        if not block or not block.get("runs"):
            continue
        print(
            "  %-14s эскалаций %d: подтвердила %d, понизила %d, подняла %d, без маршрута %d"
            % (
                mode,
                block["escalated"],
                block["llm_confirmed"],
                block["llm_lowered"],
                block["llm_raised"],
                block["llm_no_route"],
            )
        )

    recall = report.get("emergency_recall") or {}
    if recall:
        print("")
        print("Сколько золотых EMERGENCY поймал каждый уровень")
        for name in sorted(recall):
            block = recall[name]
            print("  %-24s %d из %d" % (name, block["caught"], block["gold"]))

    comparison = report.get("cascade_max_vs_only_micro") or {}
    if comparison.get("comparable"):
        verdict = "СОВПАЛ маршрут в маршрут" if comparison["identical"] else "есть расхождения"
        print("")
        print("cascade_max против only_micro: %s" % verdict)
        print(
            "  вызовов LLM %d, из них не изменивших итог %d"
            % (comparison["llm_calls_total"], comparison["llm_calls_that_changed_nothing"])
        )
        for entry in comparison["mismatches"][:5]:
            print("  расхождение: %s" % entry)

    posthoc = report.get("posthoc") or {}
    if posthoc:
        print("")
        print("Разбор постфактум, пересобрано из того же сырья, новых вызовов ноль")
        for variant in spec10.POSTHOC_VARIANTS:
            block = posthoc.get(variant)
            if not block:
                continue
            print(
                "  %-20s точность %.4f  пропущено EMERGENCY %d  ложных тревог %d  вызовов LLM %d"
                % (
                    variant,
                    block["accuracy"]["min"],
                    block["missed_emergency_worst"],
                    block["false_emergency_worst"],
                    block["llm_calls_total"],
                )
            )
            print("    %s" % spec10.POSTHOC_TITLES[variant])
    print("")
    print("Гейт, режим %s - он и решает код возврата" % spec10.MODE_CASCADE)
    for code in spec10.GATE_CODES:
        entry = report["gate"]["checks"].get(code, {})
        mark = "OK" if entry.get("passed") else "ПРОВАЛ"
        print("  [%s] %s" % (mark, spec10.GATE_TITLES[code]))
    print("  Итог: %s" % ("пройден" if report["gate"]["passed"] else "НЕ пройден"))

    extra = report.get("gate_cascade_max")
    if extra:
        print("")
        print("Те же пять пунктов для %s, справочно" % spec10.MODE_CASCADE_MAX)
        for code in spec10.GATE_CODES:
            entry = extra["checks"].get(code, {})
            mark = "OK" if entry.get("passed") else "ПРОВАЛ"
            print("  [%s] %s" % (mark, spec10.GATE_TITLES[code]))
        print("  Итог: %s" % ("пройден" if extra["passed"] else "НЕ пройден"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Отчёт по прогонам task10")
    parser.add_argument("--raw-dir", dest="raw_dir", default=spec10.RAW_DIR)
    parser.add_argument("--parity", dest="parity_path", default=spec10.PARITY_PATH)
    parser.add_argument("--model-file", dest="model_path", default=spec10.MODEL_PATH)
    parser.add_argument("--out", dest="out_path", default=spec10.REPORT_PATH)
    parser.add_argument("--train-report", dest="train_report", default=spec10.TRAIN_REPORT_PATH)
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    runs = collect_runs(args.raw_dir)
    summary = {mode: aggregate(mode_runs) for mode, mode_runs in runs.items() if mode_runs}
    parity = parity_check(args.parity_path)
    model = model_check(args.model_path)
    checks, passed = evaluate_gate(summary, parity, model, spec10.MODE_CASCADE)
    max_checks, max_passed = evaluate_gate(summary, parity, model, spec10.MODE_CASCADE_MAX)

    train_report: Dict[str, Any] = {}
    if os.path.isfile(args.train_report):
        with open(args.train_report, "r", encoding="utf-8") as handle:
            train_report = json.load(handle)

    report = {
        "raw_dir": os.path.relpath(args.raw_dir, spec10.CHALLENGE_DIR),
        "runs": {mode: mode_runs for mode, mode_runs in runs.items() if mode_runs},
        "summary": summary,
        "escalation": {
            mode: escalation_breakdown(args.raw_dir, mode) for mode in spec10.CASCADE_MODES
        },
        "emergency_recall": {
            "micro_alone": emergency_recall(args.raw_dir, spec10.MODE_ONLY_MICRO),
            "only_llm": emergency_recall(args.raw_dir, spec10.MODE_ONLY_LLM),
            "cascade": emergency_recall(args.raw_dir, spec10.MODE_CASCADE),
            "cascade_max": emergency_recall(args.raw_dir, spec10.MODE_CASCADE_MAX),
            "micro_inside_cascade": emergency_recall(
                args.raw_dir, spec10.MODE_CASCADE, use_micro_answer=True
            ),
        },
        "cascade_max_vs_only_micro": compare_modes(
            args.raw_dir, spec10.MODE_CASCADE_MAX, spec10.MODE_ONLY_MICRO
        ),
        "posthoc": posthoc_variants(args.raw_dir, model),
        "determinism": {
            spec10.MODE_ONLY_MICRO: deterministic_check(args.raw_dir, spec10.MODE_ONLY_MICRO)
        },
        "parity": parity,
        "model": model,
        "training": {
            "overlap": train_report.get("overlap", {}),
            "thresholds": train_report.get("thresholds", {}),
            "fold_validation_accuracy": train_report.get("fold_validation_accuracy"),
            "final_model": train_report.get("final_model", {}),
            "split": train_report.get("split", {}),
        },
        "gate": {"mode": spec10.MODE_CASCADE, "checks": checks, "passed": passed},
        "gate_cascade_max": {
            "mode": spec10.MODE_CASCADE_MAX,
            "checks": max_checks,
            "passed": max_passed,
            "note": (
                "справочно, код возврата не меняет. Правило слияния исправлено после первого "
                "замера, поэтому результат на том же наборе не является доказательством"
            ),
        },
    }

    directory = os.path.dirname(args.out_path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(args.out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    if not args.quiet:
        print_report(report)
        print("отчёт: %s" % args.out_path)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
