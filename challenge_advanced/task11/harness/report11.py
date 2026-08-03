"""Пересчёт метрик из raw/attacks_*.jsonl и проверка гейта целостности замера.

Гейт здесь - не про то, дырявый промпт или нет (высокий attack success rate на
defense=none - ожидаемый и допустимый результат, это и есть цель замера). Гейт
проверяет, что сам замер валиден: все мишени прогнаны, повторов достаточно,
детекторы не залипли в одном значении, в сырье не утёк ключ. Код возврата 1,
если гейт не пройден.

Запуск: python3 harness/report11.py
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import detectors
import spec11

SECRET_LIKE_PATTERN = re.compile(r"\bsk-[A-Za-z0-9]{16,}\b")


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def mean_of(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def spread_of(values: Sequence[float]) -> Dict[str, Any]:
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    return {"min": round(min(values), 4), "max": round(max(values), 4), "mean": round(mean_of(values), 4)}


def collect_runs(raw_dir: str, defense: str) -> List[Dict[str, Any]]:
    """Один run = один файл attacks_<defense>[_rN].jsonl."""
    runs: List[Dict[str, Any]] = []
    if not os.path.isdir(raw_dir):
        return runs
    prefix = spec11.RAW_FILE_PREFIX + defense
    for name in sorted(os.listdir(raw_dir)):
        if not name.startswith(prefix) or not name.endswith(spec11.RAW_FILE_EXTENSION):
            continue
        rest = name[len(spec11.RAW_FILE_PREFIX): -len(spec11.RAW_FILE_EXTENSION)]
        base, _, repeat_part = rest.partition(spec11.REPEAT_SUFFIX_PREFIX)
        if base != defense:
            continue
        repeat = int(repeat_part) if repeat_part.isdigit() else 1
        records = read_jsonl(os.path.join(raw_dir, name))
        if records:
            runs.append({"file": name, "repeat": repeat, "records": records})
    runs.sort(key=lambda run: run["repeat"])
    return runs


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def recompute_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Детекторы - чистая функция от сохранённого response, пересчитывается без новых вызовов.

    ROUTE_HIJACK не текстовый - для mode=pipeline поля уже посчитаны в run_attacks.py по фактам
    и маршруту, их не трогаем. Так 2026-08-03 правка OUT_OF_SCOPE/SAFETY_BYPASS (см. SPEC.md)
    применяется ко всему старому сырью бесплатно, без единого нового вызова к модели.
    """
    if record.get("mode") == spec11.MODE_PIPELINE or record.get("error"):
        return record
    detection = detectors.run_detectors(record.get("response", ""), record.get("target"))
    updated = dict(record)
    updated["detectors"] = detection["detectors"]
    updated["leak_markers"] = detection["leak_markers"]
    updated["safety_bypass_reason"] = detection["safety_bypass_reason"]
    updated["triggered"] = detection["triggered"]
    updated["success"] = detection["success"]
    updated["refused"] = detection[spec11.DETECTOR_REFUSED]
    return updated


def recompute_runs(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {"file": run["file"], "repeat": run["repeat"], "records": [recompute_record(r) for r in run["records"]]}
        for run in runs
    ]


def run_success_rate(records: List[Dict[str, Any]], key_field: str, key_value: Optional[str] = None) -> float:
    subset = records if key_value is None else [record for record in records if record.get(key_field) == key_value]
    ok = [record for record in subset if not record.get("error")]
    successes = sum(1 for record in ok if record.get("success"))
    return rate(successes, len(ok))


def evaluable_count(records: List[Dict[str, Any]], group_field: str, key_value: Optional[str] = None) -> int:
    subset = records if key_value is None else [record for record in records if record.get(group_field) == key_value]
    return sum(1 for record in subset if not record.get("error"))


def by_group_rates(runs: List[Dict[str, Any]], group_field: str, groups: Sequence[str]) -> Dict[str, Any]:
    """Спред success rate по повторам, плюс evaluable_total - сколько вызовов без ошибки вошло в счёт
    (нужно, чтобы rate=0.0 из-за пустого знаменателя не читался как "всё отбито")."""
    result: Dict[str, Any] = {}
    for group in groups:
        per_run_rates = [run_success_rate(run["records"], group_field, group) for run in runs]
        evaluable_total = sum(evaluable_count(run["records"], group_field, group) for run in runs)
        result[group] = dict(spread_of(per_run_rates), evaluable_total=evaluable_total)
    return result


def detector_counts(records: List[Dict[str, Any]]) -> Dict[str, int]:
    ok = [record for record in records if not record.get("error")]
    counts = {code: 0 for code in spec11.DETECTOR_CODES}
    for record in ok:
        for code in record.get("triggered") or []:
            counts[code] = counts.get(code, 0) + 1
    counts[spec11.DETECTOR_REFUSED] = sum(1 for record in ok if record.get("refused"))
    return counts


def aggregate_defense(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_records = [record for run in runs for record in run["records"]]
    overall_rates = [run_success_rate(run["records"], "target", None) for run in runs]
    latencies = [float(record.get("latency_ms") or 0) for record in all_records if not record.get("error")]
    return {
        "repeats": len(runs),
        "attacks_per_repeat": len(runs[0]["records"]) if runs else 0,
        "attack_success_rate": spread_of(overall_rates),
        "by_target": by_group_rates(runs, "target", spec11.TARGETS),
        "by_technique": by_group_rates(runs, "technique", spec11.TECHNIQUES),
        "by_split": by_group_rates(runs, "split", spec11.SPLITS),
        "by_target_technique": by_target_by_technique(runs),
        "detectors_total": detector_counts(all_records),
        "cost_usd_total": round(sum(float(record.get("cost_usd") or 0.0) for record in all_records), 8),
        "cost_usd_per_repeat": spread_of([sum(float(r.get("cost_usd") or 0.0) for r in run["records"]) for run in runs]),
        "latency_mean_ms": round(mean_of(latencies), 1),
        "errors_total": sum(1 for record in all_records if record.get("error")),
        "calls_total": len(all_records),
    }


def by_target_by_technique(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for target in spec11.TARGETS:
        result[target] = {}
        for technique in spec11.TECHNIQUES:
            per_run_rates = []
            evaluable_total = 0
            for run in runs:
                subset = [
                    record for record in run["records"]
                    if record.get("target") == target and record.get("technique") == technique and not record.get("error")
                ]
                successes = sum(1 for record in subset if record.get("success"))
                per_run_rates.append(rate(successes, len(subset)))
                evaluable_total += len(subset)
            result[target][technique] = dict(spread_of(per_run_rates), evaluable_total=evaluable_total)
    return result


def scan_secret_like(raw_dir: str) -> Dict[str, Any]:
    hits: List[str] = []
    if not os.path.isdir(raw_dir):
        return {"clean": True, "hits": hits}
    for name in sorted(os.listdir(raw_dir)):
        if not name.endswith(spec11.RAW_FILE_EXTENSION):
            continue
        path = os.path.join(raw_dir, name)
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        if SECRET_LIKE_PATTERN.search(content):
            hits.append(name)
    return {"clean": not hits, "hits": hits}


def evaluate_gate(raw_dir: str, defense_summary: Dict[str, Any], secret_scan: Dict[str, Any]) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}

    targets_present = all(
        defense_summary.get("by_target", {}).get(target, {}).get("evaluable_total", 0) > 0
        for target in spec11.TARGETS
    )
    checks[spec11.GATE_ALL_TARGETS] = {"passed": targets_present}

    repeats_ok = defense_summary.get("repeats", 0) >= spec11.DEFAULT_REPEATS
    checks[spec11.GATE_MIN_REPEATS] = {"passed": repeats_ok, "repeats": defense_summary.get("repeats", 0)}

    calls = defense_summary.get("calls_total", 0)
    errors = defense_summary.get("errors_total", 0)
    error_rate = rate(errors, calls)
    checks[spec11.GATE_ERROR_RATE] = {"passed": error_rate <= spec11.MAX_ERROR_RATE, "error_rate": error_rate}

    detectors_total = defense_summary.get("detectors_total", {})
    has_refused = detectors_total.get(spec11.DETECTOR_REFUSED, 0) > 0
    has_success = any(detectors_total.get(code, 0) > 0 for code in spec11.SUCCESS_DETECTOR_CODES)
    checks[spec11.GATE_DETECTOR_SANITY] = {"passed": has_refused and has_success}

    checks[spec11.GATE_NO_SECRET_LEAK] = {"passed": secret_scan["clean"], "hits": secret_scan["hits"]}

    passed = all(check["passed"] for check in checks.values())
    return {"checks": checks, "passed": passed}


def print_report(report: Dict[str, Any]) -> None:
    print("=== task11: attack success rate, defense=none ===")
    for defense, summary in report["by_defense"].items():
        print("\n--- защита: %s (повторов %d, атак на повтор %d) ---" % (defense, summary["repeats"], summary["attacks_per_repeat"]))
        asr = summary["attack_success_rate"]
        print("attack_success_rate: mean=%.4f min=%.4f max=%.4f" % (asr["mean"], asr["min"], asr["max"]))

        print("\nпо мишеням:")
        for target in spec11.TARGETS:
            values = summary["by_target"][target]
            print(
                "  %-8s mean=%.4f min=%.4f max=%.4f  (оценено вызовов: %d)"
                % (target, values["mean"], values["min"], values["max"], values["evaluable_total"])
            )

        print("\nпо техникам:")
        for technique in spec11.TECHNIQUES:
            values = summary["by_technique"][technique]
            print(
                "  %-14s mean=%.4f min=%.4f max=%.4f  (оценено вызовов: %d)"
                % (technique, values["mean"], values["min"], values["max"], values["evaluable_total"])
            )

        print("\nпо split:")
        for split in spec11.SPLITS:
            values = summary["by_split"][split]
            print(
                "  %-8s mean=%.4f min=%.4f max=%.4f  (оценено вызовов: %d)"
                % (split, values["mean"], values["min"], values["max"], values["evaluable_total"])
            )

        print("\nдетекторы (сумма по всем повторам):")
        for code in spec11.DETECTOR_CODES + (spec11.DETECTOR_REFUSED,):
            print("  %-16s %d" % (code, summary["detectors_total"].get(code, 0)))

        print(
            "\nцена суммарно %.6f USD (за повтор: mean=%.6f), задержка средняя %.1f мс, ошибок %d из %d вызовов"
            % (
                summary["cost_usd_total"],
                summary["cost_usd_per_repeat"]["mean"],
                summary["latency_mean_ms"],
                summary["errors_total"],
                summary["calls_total"],
            )
        )

    print("\n=== правка детекторов 2026-08-03 - до/после, то же сырьё, новых вызовов 0 ===")
    for defense, comparison in report["detector_fix_comparison"].items():
        before, after = comparison["attack_success_rate"]["before"], comparison["attack_success_rate"]["after"]
        print(
            "  %s: ASR mean %.4f -> %.4f" % (defense, before["mean"], after["mean"])
        )
        for target in spec11.TARGETS:
            tb = comparison["by_target"][target]["before"]
            ta = comparison["by_target"][target]["after"]
            print("    %-8s mean %.4f -> %.4f" % (target, tb["mean"], ta["mean"]))
        db, da = comparison["detectors_total"]["before"], comparison["detectors_total"]["after"]
        for code in spec11.DETECTOR_CODES:
            if db.get(code, 0) != da.get(code, 0):
                print("    %-16s %d -> %d" % (code, db.get(code, 0), da.get(code, 0)))

    print("\n=== гейт целостности замера (на исправленных детекторах) ===")
    for code in spec11.GATE_CODES:
        entry = report["gate"]["checks"].get(code, {})
        mark = "OK" if entry.get("passed") else "ПРОВАЛ"
        print("  [%s] %s" % (mark, spec11.GATE_TITLES[code]))
    print("  Итог: %s" % ("пройден" if report["gate"]["passed"] else "НЕ пройден"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Отчёт по прогонам task11")
    parser.add_argument("--raw-dir", dest="raw_dir", default=spec11.RAW_DIR)
    parser.add_argument("--out", dest="out_path", default=spec11.REPORT_PATH)
    parser.add_argument("--quiet", action="store_true")
    return parser


def detector_fix_comparison(legacy: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """До/после правки детекторов 2026-08-03 (SPEC.md), на одном и том же сырье, без новых вызовов."""
    return {
        "attack_success_rate": {"before": legacy["attack_success_rate"], "after": current["attack_success_rate"]},
        "by_target": {
            target: {"before": legacy["by_target"][target], "after": current["by_target"][target]}
            for target in spec11.TARGETS
        },
        "detectors_total": {"before": legacy["detectors_total"], "after": current["detectors_total"]},
    }


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    by_defense: Dict[str, Any] = {}
    legacy_by_defense: Dict[str, Any] = {}
    for defense in spec11.DEFENSES:
        runs = collect_runs(args.raw_dir, defense)
        if runs:
            legacy_by_defense[defense] = aggregate_defense(runs)
            by_defense[defense] = aggregate_defense(recompute_runs(runs))

    if not by_defense:
        sys.stderr.write("В %s нет сырья ни по одному слою защиты. Сначала запусти run_attacks.py.\n" % args.raw_dir)
        return spec11.EXIT_DATA_ERROR

    secret_scan = scan_secret_like(args.raw_dir)
    gate_defense = spec11.DEFENSE_NONE if spec11.DEFENSE_NONE in by_defense else next(iter(by_defense))
    gate = evaluate_gate(args.raw_dir, by_defense[gate_defense], secret_scan)
    fix_comparison = {
        defense: detector_fix_comparison(legacy_by_defense[defense], by_defense[defense])
        for defense in by_defense
    }

    report = {
        "raw_dir": os.path.relpath(args.raw_dir, spec11.CHALLENGE_DIR),
        "detector_fix_comparison": fix_comparison,
        "by_defense": by_defense,
        "secret_scan": secret_scan,
        "gate": gate,
        "gate_defense": gate_defense,
    }

    directory = os.path.dirname(args.out_path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(args.out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    if not args.quiet:
        print_report(report)
        print("\nотчёт: %s" % args.out_path)
    return spec11.EXIT_OK if gate["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
