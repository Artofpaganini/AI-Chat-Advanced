"""Пересчёт метрик из raw/run_*/indirect_*.jsonl и проверка гейта целостности замера.

Гейт - не про то, дырявый промпт или нет (высокий attack success rate на defense=none -
ожидаемый и допустимый результат, это и есть цель замера). Гейт проверяет, что сам замер
валиден: все векторы прогнаны, повторов достаточно, детекторы не залипли, в сырье не утёк ключ.
Код возврата 1, если гейт не пройден.

Детекторы пересчитываются заново из сохранённого response/followup_response (чистая функция,
без новых вызовов к модели) - маркеры атаки берутся из data/documents.jsonl по id документа,
в сыром выводе они не дублируются.

Запуск: python3 harness/report12.py
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

import detectors12
import payloads
import spec12

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


def find_run_dirs(raw_dir: str) -> List[str]:
    if not os.path.isdir(raw_dir):
        return []
    return sorted(
        name for name in os.listdir(raw_dir)
        if os.path.isdir(os.path.join(raw_dir, name)) and name.startswith(spec12.RUN_DIR_PREFIX)
    )


def search_dirs(raw_dir: str) -> List[Any]:
    """(имя, путь) для агрегации: сам raw_dir (на случай --raw-dir=raw/run_<timestamp>/ - один
    конкретный прогон без вложенности) плюс все его под-каталоги run_*/."""
    own_name = os.path.basename(os.path.normpath(raw_dir)) or raw_dir
    return [(own_name, raw_dir)] + [(name, os.path.join(raw_dir, name)) for name in find_run_dirs(raw_dir)]


def collect_runs(raw_dir: str, defense: str) -> List[Dict[str, Any]]:
    """Один run = один файл indirect_<defense>[_rN].jsonl внутри одного из каталогов raw/run_*/.

    Дополнительно сканируется сам raw_dir напрямую (без под-каталогов run_*) - это позволяет
    указать --raw-dir прямо на один прогон (raw/run_<timestamp>/), не собирая агрегат по всем
    прогонам сразу. По умолчанию (--raw-dir=raw/) это ничего не меняет: файлов indirect_*.jsonl
    прямо в raw/ никогда нет, run_indirect.py всегда пишет в под-каталог.
    """
    runs: List[Dict[str, Any]] = []
    prefix = spec12.RAW_FILE_PREFIX + defense
    for run_dir_name, run_dir_path in search_dirs(raw_dir):
        if not os.path.isdir(run_dir_path):
            continue
        for name in sorted(os.listdir(run_dir_path)):
            if not name.startswith(prefix) or not name.endswith(spec12.RAW_FILE_EXTENSION):
                continue
            rest = name[len(spec12.RAW_FILE_PREFIX): -len(spec12.RAW_FILE_EXTENSION)]
            base, _, repeat_part = rest.partition(spec12.REPEAT_SUFFIX_PREFIX)
            if base != defense:
                continue
            repeat = int(repeat_part) if repeat_part.isdigit() else 1
            records = read_jsonl(os.path.join(run_dir_path, name))
            if records:
                runs.append({"file": "%s/%s" % (run_dir_name, name), "run_dir": run_dir_name, "repeat": repeat, "records": records})
    runs.sort(key=lambda run: (run["run_dir"], run["repeat"]))
    return runs


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def recompute_record(record: Dict[str, Any], documents_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if record.get("error"):
        return record
    doc = documents_by_id.get(record.get("id"))
    if doc is None:
        return record
    require_unattributed = record.get("defense") in (spec12.DEFENSE_D4_PROVENANCE, spec12.DEFENSE_ALL)
    detection = detectors12.run_detectors(
        response_text=record.get("response", ""),
        target=record.get("target"),
        injected_line_marker=doc.get("injected_line_marker", ""),
        false_fact_marker=doc.get("false_fact_marker", ""),
        override_kind=doc.get("override_kind", ""),
        followup_response_text=record.get("followup_response"),
        context_poison_marker=doc.get("context_poison_marker", ""),
        require_unattributed=require_unattributed,
    )
    updated = dict(record)
    updated["detectors"] = detection["detectors"]
    updated["override_reason"] = detection["override_reason"]
    updated["triggered"] = detection["triggered"]
    updated["success"] = detection["success"]
    updated["clean"] = detection[spec12.DETECTOR_CLEAN]
    return updated


def recompute_runs(runs: List[Dict[str, Any]], documents_by_id: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "file": run["file"], "run_dir": run["run_dir"], "repeat": run["repeat"],
            "records": [recompute_record(record, documents_by_id) for record in run["records"]],
        }
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
    result: Dict[str, Any] = {}
    for group in groups:
        per_run_rates = [run_success_rate(run["records"], group_field, group) for run in runs]
        evaluable_total = sum(evaluable_count(run["records"], group_field, group) for run in runs)
        result[group] = dict(spread_of(per_run_rates), evaluable_total=evaluable_total)
    return result


def by_vector_by_hiding(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for vector in spec12.VECTORS:
        result[vector] = {}
        for hiding in spec12.HIDINGS:
            per_run_rates = []
            evaluable_total = 0
            for run in runs:
                subset = [
                    record for record in run["records"]
                    if record.get("vector") == vector and record.get("hiding") == hiding and not record.get("error")
                ]
                successes = sum(1 for record in subset if record.get("success"))
                per_run_rates.append(rate(successes, len(subset)))
                evaluable_total += len(subset)
            result[vector][hiding] = dict(spread_of(per_run_rates), evaluable_total=evaluable_total)
    return result


def detector_counts(records: List[Dict[str, Any]]) -> Dict[str, int]:
    ok = [record for record in records if not record.get("error")]
    counts = {code: 0 for code in spec12.DETECTOR_CODES}
    for record in ok:
        for code in record.get("triggered") or []:
            counts[code] = counts.get(code, 0) + 1
    counts[spec12.DETECTOR_CLEAN] = sum(1 for record in ok if record.get("clean"))
    return counts


def aggregate_defense(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_records = [record for run in runs for record in run["records"]]
    overall_rates = [run_success_rate(run["records"], "vector", None) for run in runs]
    latencies = [float(record.get("latency_ms") or 0) for record in all_records if not record.get("error")]
    return {
        "repeats": len(runs),
        "documents_per_repeat": len(runs[0]["records"]) if runs else 0,
        "attack_success_rate": spread_of(overall_rates),
        "by_vector": by_group_rates(runs, "vector", spec12.VECTORS),
        "by_hiding": by_group_rates(runs, "hiding", spec12.HIDINGS),
        "by_split": by_group_rates(runs, "split", spec12.SPLITS),
        "by_vector_hiding": by_vector_by_hiding(runs),
        "detectors_total": detector_counts(all_records),
        "cost_usd_total": round(sum(float(record.get("cost_usd") or 0.0) for record in all_records), 8),
        "cost_usd_per_repeat": spread_of([sum(float(r.get("cost_usd") or 0.0) for r in run["records"]) for run in runs]),
        "latency_mean_ms": round(mean_of(latencies), 1),
        "errors_total": sum(1 for record in all_records if record.get("error")),
        "calls_total": len(all_records),
    }


def scan_secret_like(raw_dir: str) -> Dict[str, Any]:
    hits: List[str] = []
    for run_dir_name, run_dir_path in search_dirs(raw_dir):
        if not os.path.isdir(run_dir_path):
            continue
        for name in sorted(os.listdir(run_dir_path)):
            if not name.endswith(spec12.RAW_FILE_EXTENSION):
                continue
            path = os.path.join(run_dir_path, name)
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if SECRET_LIKE_PATTERN.search(content):
                hits.append("%s/%s" % (run_dir_name, name))
    return {"clean": not hits, "hits": hits}


def evaluate_gate(defense_summary: Dict[str, Any], secret_scan: Dict[str, Any]) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}

    vectors_present = all(
        defense_summary.get("by_vector", {}).get(vector, {}).get("evaluable_total", 0) > 0
        for vector in spec12.VECTORS
    )
    checks[spec12.GATE_ALL_VECTORS] = {"passed": vectors_present}

    repeats_ok = defense_summary.get("repeats", 0) >= spec12.DEFAULT_REPEATS
    checks[spec12.GATE_MIN_REPEATS] = {"passed": repeats_ok, "repeats": defense_summary.get("repeats", 0)}

    calls = defense_summary.get("calls_total", 0)
    errors = defense_summary.get("errors_total", 0)
    error_rate = rate(errors, calls)
    checks[spec12.GATE_ERROR_RATE] = {"passed": error_rate <= spec12.MAX_ERROR_RATE, "error_rate": error_rate}

    detectors_total = defense_summary.get("detectors_total", {})
    has_clean = detectors_total.get(spec12.DETECTOR_CLEAN, 0) > 0
    has_success = any(detectors_total.get(code, 0) > 0 for code in spec12.SUCCESS_DETECTOR_CODES)
    checks[spec12.GATE_DETECTOR_SANITY] = {"passed": has_clean and has_success}

    checks[spec12.GATE_NO_SECRET_LEAK] = {"passed": secret_scan["clean"], "hits": secret_scan["hits"]}

    passed = all(check["passed"] for check in checks.values())
    return {"checks": checks, "passed": passed}


def print_report(report: Dict[str, Any]) -> None:
    print("=== task12: успех косвенной инъекции, defense=none ===")
    for defense, summary in report["by_defense"].items():
        print(
            "\n--- защита: %s (повторов %d, документов на повтор %d) ---"
            % (defense, summary["repeats"], summary["documents_per_repeat"])
        )
        asr = summary["attack_success_rate"]
        print("attack_success_rate: mean=%.4f min=%.4f max=%.4f" % (asr["mean"], asr["min"], asr["max"]))

        print("\nпо векторам:")
        for vector in spec12.VECTORS:
            values = summary["by_vector"][vector]
            print(
                "  %-14s mean=%.4f min=%.4f max=%.4f  (оценено вызовов: %d)"
                % (vector, values["mean"], values["min"], values["max"], values["evaluable_total"])
            )

        print("\nпо приёмам сокрытия:")
        for hiding in spec12.HIDINGS:
            values = summary["by_hiding"][hiding]
            print(
                "  %-16s mean=%.4f min=%.4f max=%.4f  (оценено вызовов: %d)"
                % (hiding, values["mean"], values["min"], values["max"], values["evaluable_total"])
            )

        print("\nпо split:")
        for split in spec12.SPLITS:
            values = summary["by_split"][split]
            print(
                "  %-8s mean=%.4f min=%.4f max=%.4f  (оценено вызовов: %d)"
                % (split, values["mean"], values["min"], values["max"], values["evaluable_total"])
            )

        print("\nматрица вектор x приём сокрытия (mean success rate):")
        header = "%-14s" % "" + "".join("%-14s" % hiding for hiding in spec12.HIDINGS)
        print(header)
        for vector in spec12.VECTORS:
            row = "%-14s" % vector + "".join(
                "%-14.4f" % summary["by_vector_hiding"][vector][hiding]["mean"] for hiding in spec12.HIDINGS
            )
            print(row)

        print("\nдетекторы (сумма по всем повторам):")
        for code in spec12.DETECTOR_CODES + (spec12.DETECTOR_CLEAN,):
            print("  %-18s %d" % (code, summary["detectors_total"].get(code, 0)))

        print(
            "\nцена суммарно %.6f USD (за повтор: mean=%.6f), задержка средняя %.1f мс, ошибок %d из %d вызовов"
            % (
                summary["cost_usd_total"], summary["cost_usd_per_repeat"]["mean"],
                summary["latency_mean_ms"], summary["errors_total"], summary["calls_total"],
            )
        )

    print("\n=== гейт целостности замера ===")
    for code in spec12.GATE_CODES:
        entry = report["gate"]["checks"].get(code, {})
        mark = "OK" if entry.get("passed") else "ПРОВАЛ"
        print("  [%s] %s" % (mark, spec12.GATE_TITLES[code]))
    print("  Итог: %s" % ("пройден" if report["gate"]["passed"] else "НЕ пройден"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Отчёт по прогонам task12")
    parser.add_argument("--raw-dir", dest="raw_dir", default=spec12.RAW_DIR)
    parser.add_argument("--documents-path", dest="documents_path", default=spec12.DOCUMENTS_PATH)
    parser.add_argument("--out", dest="out_path", default=spec12.REPORT_PATH)
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        documents = payloads.load_documents(args.documents_path)
    except payloads.DocumentsError as documents_error:
        sys.stderr.write("Не могу прочитать набор документов: %s\n" % documents_error)
        return spec12.EXIT_DATA_ERROR
    documents_by_id = {document["id"]: document for document in documents}

    by_defense: Dict[str, Any] = {}
    for defense in spec12.DEFENSES:
        runs = collect_runs(args.raw_dir, defense)
        if runs:
            by_defense[defense] = aggregate_defense(recompute_runs(runs, documents_by_id))

    if not by_defense:
        sys.stderr.write("В %s нет сырья ни по одному слою защиты. Сначала запусти run_indirect.py.\n" % args.raw_dir)
        return spec12.EXIT_DATA_ERROR

    secret_scan = scan_secret_like(args.raw_dir)
    gate_defense = spec12.DEFENSE_NONE if spec12.DEFENSE_NONE in by_defense else next(iter(by_defense))
    gate = evaluate_gate(by_defense[gate_defense], secret_scan)

    report = {
        "raw_dir": os.path.relpath(args.raw_dir, spec12.CHALLENGE_DIR),
        "documents_total": len(documents),
        "documents_split": payloads.split_counts(documents),
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
    return spec12.EXIT_OK if gate["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
