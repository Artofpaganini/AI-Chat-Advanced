"""Отчёт по двум вариантам инференса: монолит против трёхэтапной цепочки.

Читает raw/monolithic_runs*.jsonl и raw/multistage_runs*.jsonl, считает метрики SPEC раздел 4,
печатает таблицы и пишет JSON. Несколько прогонов одного варианта сводятся в медиану и диапазон,
пропущенные экстренные берутся по ХУДШЕМУ прогону - решение принимается по нему.

Кейсы, где ожидается отказ (expected_status = FAIL), из точности исключены, как в task7:
там проверяется не маршрут, а способность варианта не ответить наугад.

Гейт один: если у цепочки пропущенных экстренных больше, чем у монолита, выход с кодом 1.

Запуск: python3 harness/stages_report.py
        python3 harness/stages_report.py --runs raw --out results/stages_report.json
"""

import argparse
import json
import os
import statistics
import sys
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import stages_spec

sys.path.insert(0, stages_spec.TASK7_HARNESS_DIR)

import report
import run_eval
import spec7

AGE_AS_METRIC_MARKERS = ("age", "месяц", "мес.", "лет", "год", "недел")
MODE_TITLES = {
    stages_spec.MODE_MONOLITHIC: "монолит, один вызов",
    stages_spec.MODE_MULTISTAGE: "цепочка, три этапа",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Сводка по монолитному и трёхэтапному инференсу триажа ALVA.",
    )
    parser.add_argument("--runs", nargs="*", default=[stages_spec.RAW_DIR])
    parser.add_argument("--cases", dest="cases_paths", nargs="*", default=[stages_spec.CASES_PATH])
    parser.add_argument("--out", dest="out_path", default=stages_spec.DEFAULT_REPORT_PATH)
    return parser


def route_severity(route: Optional[str]) -> int:
    if route not in stages_spec.SEVERITY:
        return -1
    return stages_spec.SEVERITY[route]


def mode_of_file(name: str) -> Optional[str]:
    for mode in stages_spec.MODES:
        if name.startswith(mode + stages_spec.RUNS_FILE_SUFFIX):
            return mode
    return None


def collect_paths(inputs: List[str]) -> List[Tuple[str, str]]:
    found: List[Tuple[str, str]] = []
    for item in inputs:
        if os.path.isdir(item):
            for name in sorted(os.listdir(item)):
                if not name.endswith(stages_spec.RUNS_FILE_EXTENSION):
                    continue
                mode = mode_of_file(name)
                if mode is not None:
                    found.append((mode, os.path.join(item, name)))
            continue
        if os.path.isfile(item):
            mode = mode_of_file(os.path.basename(item))
            if mode is not None:
                found.append((mode, item))
    return found


def read_records(path: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def usage_of(stage: Dict[str, Any]) -> Dict[str, int]:
    usage = stage.get("usage")
    if not isinstance(usage, dict):
        return {}
    return usage


def token_value(usage: Dict[str, int], key: str) -> int:
    value = usage.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def empty_stage_block() -> Dict[str, Any]:
    return {
        "calls": 0,
        "format_failures": 0,
        "first_failures": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "latency_ms": 0,
    }


def facts_of(record: Dict[str, Any]) -> Dict[str, Any]:
    for stage in record.get("stages") or []:
        if stage.get("stage") == stages_spec.STAGE_PARSE:
            parsed = stage.get("parsed")
            if isinstance(parsed, dict):
                return parsed
    return {}


def age_looks_like_metric(metrics: str) -> bool:
    value = (metrics or "").lower()
    if value == stages_spec.NONE_VALUE:
        return False
    return any(marker in value for marker in AGE_AS_METRIC_MARKERS)


def summarize_run(
    records: List[Dict[str, Any]], cases: Dict[str, Dict[str, Any]], mode: str, path: str
) -> Dict[str, Any]:
    stage_blocks: Dict[str, Dict[str, Any]] = {}
    violation_counts: Dict[str, int] = {}
    group_stats: Dict[str, List[int]] = {group: [0, 0] for group in stages_spec.GROUPS}
    question_types: Dict[str, int] = {}
    route_graded = 0
    correct = 0
    missed_emergency = 0
    false_emergency = 0
    expected_fail = 0
    expected_fail_handled = 0
    unknown_cases = 0
    errors = 0
    calls = 0
    cost = 0.0
    latencies: List[float] = []
    metrics_none = 0
    metrics_with_age = 0
    care_graded = 0
    care_correct = 0

    for record in records:
        case_id = str(record.get("case_id"))
        calls += int(record.get("calls") or 0)
        value = record.get("total_cost_usd")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            cost += float(value)
        latency = record.get("total_latency_ms")
        if isinstance(latency, int):
            latencies.append(float(latency))
        if record.get("error"):
            errors += 1

        for stage in record.get("stages") or []:
            name = str(stage.get("stage"))
            block = stage_blocks.setdefault(name, empty_stage_block())
            block["calls"] += 1
            usage = usage_of(stage)
            block["tokens_in"] += token_value(usage, "prompt_tokens")
            block["tokens_out"] += token_value(usage, "completion_tokens")
            stage_cost = stage.get("cost_usd")
            if isinstance(stage_cost, (int, float)) and not isinstance(stage_cost, bool):
                block["cost_usd"] += float(stage_cost)
            stage_latency = stage.get("latency_ms")
            if isinstance(stage_latency, int):
                block["latency_ms"] += stage_latency
            codes = [str(code) for code in stage.get("violations") or []]
            if codes:
                block["format_failures"] += 1
            for code in codes:
                violation_counts[code] = violation_counts.get(code, 0) + 1

        failed_stage = record.get("failed_stage")
        if failed_stage:
            block = stage_blocks.setdefault(str(failed_stage), empty_stage_block())
            block["first_failures"] += 1

        if mode == stages_spec.MODE_MULTISTAGE:
            facts = facts_of(record)
            if facts:
                question_type = str(facts.get(stages_spec.F_QUESTION_TYPE) or "-")
                question_types[question_type] = question_types.get(question_type, 0) + 1
                metrics = str(facts.get(stages_spec.F_METRICS) or stages_spec.NONE_VALUE)
                if metrics == stages_spec.NONE_VALUE:
                    metrics_none += 1
                elif age_looks_like_metric(metrics):
                    metrics_with_age += 1

        case = cases.get(case_id)
        if case is None:
            unknown_cases += 1
            continue
        if report.expects_fail(case):
            expected_fail += 1
            if record.get("route") is None:
                expected_fail_handled += 1
            continue

        gold = str(case.get("expected_route"))
        predicted = record.get("route")
        group = str(case.get("group", "-"))
        route_graded += 1
        bucket = group_stats.setdefault(group, [0, 0])
        bucket[1] += 1
        if predicted == gold:
            correct += 1
            bucket[0] += 1
        if gold == spec7.ROUTE_EMERGENCY and route_severity(predicted) < stages_spec.SEVERITY[gold]:
            missed_emergency += 1
        if gold != spec7.ROUTE_EMERGENCY and predicted == spec7.ROUTE_EMERGENCY:
            false_emergency += 1
        if mode == stages_spec.MODE_MULTISTAGE:
            facts = facts_of(record)
            if facts.get(stages_spec.F_QUESTION_TYPE) == stages_spec.QT_CARE:
                care_graded += 1
                if predicted == gold:
                    care_correct += 1

    for block in stage_blocks.values():
        block["cost_usd"] = round(block["cost_usd"], 8)

    return {
        "mode": mode,
        "path": path,
        "file": os.path.basename(path),
        "total": len(records),
        "route_graded": route_graded,
        "correct": correct,
        "accuracy": round(correct / route_graded, 4) if route_graded else 0.0,
        "missed_emergency": missed_emergency,
        "false_emergency": false_emergency,
        "expected_fail": expected_fail,
        "expected_fail_handled": expected_fail_handled,
        "unknown_cases": unknown_cases,
        "errors": errors,
        "calls": calls,
        "cost_usd": round(cost, 6),
        "latency_p50_ms": int(report.percentile(latencies, stages_spec.PERCENTILE_50)),
        "latency_p95_ms": int(report.percentile(latencies, stages_spec.PERCENTILE_95)),
        "groups": {
            group: {
                "graded": bucket[1],
                "correct": bucket[0],
                "accuracy": round(bucket[0] / bucket[1], 4) if bucket[1] else 0.0,
            }
            for group, bucket in group_stats.items()
        },
        "stages": stage_blocks,
        "violations": violation_counts,
        "stage_failures": sum(block["format_failures"] for block in stage_blocks.values()),
        "question_types": question_types,
        "metrics_none": metrics_none,
        "metrics_with_age": metrics_with_age,
        "care_graded": care_graded,
        "care_accuracy": round(care_correct / care_graded, 4) if care_graded else 0.0,
    }


def spread(values: List[float], as_integer: bool = False) -> Dict[str, Any]:
    if not values:
        return {"median": 0, "min": 0, "max": 0}
    median = statistics.median(values)
    if as_integer:
        return {"median": int(median), "min": int(min(values)), "max": int(max(values))}
    return {
        "median": round(float(median), 6),
        "min": round(float(min(values)), 6),
        "max": round(float(max(values)), 6),
    }


def merge_counts(runs: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for run in runs:
        for name, value in (run.get(key) or {}).items():
            counts[name] = counts.get(name, 0) + int(value)
    return counts


def merge_stage_blocks(runs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for run in runs:
        for name, block in run["stages"].items():
            target = merged.setdefault(name, empty_stage_block())
            for field_name, value in block.items():
                target[field_name] += value
    for block in merged.values():
        block["cost_usd"] = round(block["cost_usd"], 8)
    return merged


def merge_groups(runs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for run in runs:
        for group, block in run["groups"].items():
            target = merged.setdefault(group, {"graded": 0, "correct": 0, "accuracy": 0.0})
            target["graded"] += block["graded"]
            target["correct"] += block["correct"]
    for block in merged.values():
        block["accuracy"] = (
            round(block["correct"] / block["graded"], 4) if block["graded"] else 0.0
        )
    return merged


def aggregate_mode(mode: str, runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "mode": mode,
        "runs": len(runs),
        "files": [run["file"] for run in runs],
        "cases": runs[0]["total"] if runs else 0,
        "accuracy": spread([run["accuracy"] for run in runs]),
        "missed_emergency": spread([float(run["missed_emergency"]) for run in runs], True),
        "missed_emergency_worst": max(run["missed_emergency"] for run in runs) if runs else 0,
        "false_emergency": spread([float(run["false_emergency"]) for run in runs], True),
        "false_emergency_worst": max(run["false_emergency"] for run in runs) if runs else 0,
        "stage_failures": spread([float(run["stage_failures"]) for run in runs], True),
        "latency_p50_ms": spread([float(run["latency_p50_ms"]) for run in runs], True),
        "latency_p95_ms": spread([float(run["latency_p95_ms"]) for run in runs], True),
        "cost_usd": spread([run["cost_usd"] for run in runs]),
        "calls": spread([float(run["calls"]) for run in runs], True),
        "errors": spread([float(run["errors"]) for run in runs], True),
        "expected_fail": runs[0]["expected_fail"] if runs else 0,
        "expected_fail_handled": spread(
            [float(run["expected_fail_handled"]) for run in runs], True
        ),
        "groups": merge_groups(runs),
        "group_accuracy_spread": {
            group: spread([run["groups"].get(group, {}).get("accuracy", 0.0) for run in runs])
            for group in stages_spec.GROUPS
        },
        "stages": merge_stage_blocks(runs),
        "violations": merge_counts(runs, "violations"),
        "question_types": merge_counts(runs, "question_types"),
        "metrics_none": sum(run["metrics_none"] for run in runs),
        "metrics_with_age": sum(run["metrics_with_age"] for run in runs),
        "care_accuracy": spread([run["care_accuracy"] for run in runs]),
        "care_graded": sum(run["care_graded"] for run in runs),
    }


def format_spread(block: Dict[str, Any], template: str = "%.4f") -> str:
    if block["min"] == block["max"]:
        return template % block["median"]
    return "%s (%s..%s)" % (
        template % block["median"],
        template % block["min"],
        template % block["max"],
    )


def format_int_spread(block: Dict[str, Any]) -> str:
    if block["min"] == block["max"]:
        return str(int(block["median"]))
    return "%d (%d..%d)" % (block["median"], block["min"], block["max"])


def print_main_table(aggregates: Dict[str, Dict[str, Any]]) -> None:
    header = "%-12s %-24s %-14s %-14s %-12s %-14s %-10s %s" % (
        "вариант",
        "точность",
        "пропуск EMG",
        "ложных EMG",
        "вызовов",
        "цена, USD",
        "p50, мс",
        "p95, мс",
    )
    sys.stdout.write("\nОбщая сводка\n")
    sys.stdout.write(header + "\n")
    sys.stdout.write("-" * len(header) + "\n")
    for mode in stages_spec.MODES:
        aggregate = aggregates.get(mode)
        if aggregate is None:
            continue
        sys.stdout.write(
            "%-12s %-24s %-14s %-14s %-12s %-14s %-10s %s\n"
            % (
                mode,
                format_spread(aggregate["accuracy"]),
                "%d худший" % aggregate["missed_emergency_worst"],
                "%d худший" % aggregate["false_emergency_worst"],
                format_int_spread(aggregate["calls"]),
                format_spread(aggregate["cost_usd"], "%.6f"),
                format_int_spread(aggregate["latency_p50_ms"]),
                format_int_spread(aggregate["latency_p95_ms"]),
            )
        )
    sys.stdout.write(
        "Пропущенные и ложные экстренные показаны по худшему прогону, остальное - медиана "
        "и диапазон по прогонам.\n"
    )


def print_groups(aggregates: Dict[str, Dict[str, Any]]) -> None:
    header = "%-12s %-12s %-10s %-10s %s" % (
        "вариант",
        "группа",
        "кейсов",
        "верно",
        "точность",
    )
    sys.stdout.write("\nРазбивка по группам кейсов, гипотезы 1 и 3\n")
    sys.stdout.write(header + "\n")
    sys.stdout.write("-" * len(header) + "\n")
    for mode in stages_spec.MODES:
        aggregate = aggregates.get(mode)
        if aggregate is None:
            continue
        for group in stages_spec.GROUPS:
            block = aggregate["groups"].get(group)
            if block is None:
                continue
            sys.stdout.write(
                "%-12s %-12s %-10d %-10d %s\n"
                % (
                    mode,
                    group,
                    block["graded"],
                    block["correct"],
                    format_spread(aggregate["group_accuracy_spread"][group])
                    if block["graded"]
                    else stages_spec.NOT_AVAILABLE,
                )
            )
    sys.stdout.write(
        "Кейсы с ожидаемым отказом в точность не входят, показано отказов из таких кейсов: %s.\n"
        % ", ".join(
            "%s %s из %d"
            % (
                mode,
                format_int_spread(aggregates[mode]["expected_fail_handled"]),
                aggregates[mode]["expected_fail"],
            )
            for mode in stages_spec.MODES
            if mode in aggregates
        )
    )


def print_failures(aggregates: Dict[str, Dict[str, Any]]) -> None:
    header = "%-12s %-24s %-10s %-18s %s" % (
        "вариант",
        "этап",
        "вызовов",
        "битый формат",
        "первым сломался",
    )
    sys.stdout.write("\nГде ломается\n")
    sys.stdout.write(header + "\n")
    sys.stdout.write("-" * len(header) + "\n")
    for mode in stages_spec.MODES:
        aggregate = aggregates.get(mode)
        if aggregate is None:
            continue
        for stage in stages_spec.ALL_STAGES:
            block = aggregate["stages"].get(stage)
            if block is None:
                continue
            sys.stdout.write(
                "%-12s %-24s %-10d %-18d %d\n"
                % (
                    mode,
                    stages_spec.STAGE_TITLES[stage],
                    block["calls"],
                    block["format_failures"],
                    block["first_failures"],
                )
            )
    sys.stdout.write("\nКоды нарушений\n")
    for mode in stages_spec.MODES:
        aggregate = aggregates.get(mode)
        if aggregate is None:
            continue
        violations = aggregate["violations"]
        if not violations:
            sys.stdout.write("  %-12s нарушений нет\n" % mode)
            continue
        parts = [
            "%s %d" % (code, count)
            for code, count in sorted(violations.items(), key=lambda item: (-item[1], item[0]))
        ]
        sys.stdout.write("  %-12s %s\n" % (mode, ", ".join(parts)))


def print_tokens(aggregates: Dict[str, Dict[str, Any]]) -> None:
    header = "%-12s %-24s %-12s %-12s %-12s %-12s %s" % (
        "вариант",
        "этап",
        "tokens_in",
        "tokens_out",
        "цена, USD",
        "доля цены",
        "время, мс",
    )
    sys.stdout.write("\nРасход по этапам\n")
    sys.stdout.write(header + "\n")
    sys.stdout.write("-" * len(header) + "\n")
    for mode in stages_spec.MODES:
        aggregate = aggregates.get(mode)
        if aggregate is None:
            continue
        total_cost = sum(block["cost_usd"] for block in aggregate["stages"].values())
        for stage in stages_spec.ALL_STAGES:
            block = aggregate["stages"].get(stage)
            if block is None:
                continue
            share = block["cost_usd"] / total_cost if total_cost else 0.0
            sys.stdout.write(
                "%-12s %-24s %-12d %-12d %-12.6f %-12s %d\n"
                % (
                    mode,
                    stages_spec.STAGE_TITLES[stage],
                    block["tokens_in"],
                    block["tokens_out"],
                    block["cost_usd"],
                    "%.0f%%" % (share * 100),
                    block["latency_ms"],
                )
            )
    sys.stdout.write("Суммы по всем прогонам варианта, не по одному.\n")
    sys.stdout.write(
        "Часть разницы в цене - не декомпозиция: монолит текста родителю не пишет вовсе, "
        "а этап 3 пишет. Чистая цена решения - это этапы 1 и 2 против монолита.\n"
    )


def hypothesis_lines(aggregates: Dict[str, Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    mono = aggregates.get(stages_spec.MODE_MONOLITHIC)
    multi = aggregates.get(stages_spec.MODE_MULTISTAGE)
    if mono is None or multi is None:
        lines.append("Оба варианта не прогнаны, гипотезы не проверяются.")
        return lines
    for number, group in ((1, spec7.GROUP_BORDERLINE), (3, spec7.GROUP_NOISY)):
        mono_block = mono["groups"].get(group, {})
        multi_block = multi["groups"].get(group, {})
        if not mono_block.get("graded") or not multi_block.get("graded"):
            lines.append(
                "Гипотеза %d (%s): в прогоне нет кейсов группы %s, проверить нечем."
                % (number, stages_spec.HYPOTHESES[number], group)
            )
            continue
        mono_value = mono_block.get("accuracy", 0.0)
        multi_value = multi_block.get("accuracy", 0.0)
        if multi_value > mono_value:
            verdict = "подтверждается"
        elif multi_value == mono_value:
            verdict = "разницы нет"
        else:
            verdict = "не подтверждается"
        lines.append(
            "Гипотеза %d (%s): монолит %.4f, цепочка %.4f -> %s."
            % (number, stages_spec.HYPOTHESES[number], mono_value, multi_value, verdict)
        )
    mono_cost = mono["cost_usd"]["median"]
    multi_cost = multi["cost_usd"]["median"]
    ratio = multi_cost / mono_cost if mono_cost else 0.0
    lines.append(
        "Гипотеза 2 (%s): цена %.6f против %.6f, во сколько раз дороже - %.2f; "
        "задержка p50 %d против %d мс."
        % (
            stages_spec.HYPOTHESES[2],
            multi_cost,
            mono_cost,
            ratio,
            multi["latency_p50_ms"]["median"],
            mono["latency_p50_ms"]["median"],
        )
    )
    lines.append(
        "Гипотеза 4 (%s): этап 1 сказал METRICS=none на %d разборах, возраст утёк в показатели "
        "%d раз; распределение QUESTION_TYPE %s; точность на CARE %s."
        % (
            stages_spec.HYPOTHESES[4],
            multi["metrics_none"],
            multi["metrics_with_age"],
            ", ".join(
                "%s %d" % (name, count) for name, count in sorted(multi["question_types"].items())
            )
            or "пусто",
            format_spread(multi["care_accuracy"]),
        )
    )
    return lines


def print_hypotheses(aggregates: Dict[str, Dict[str, Any]]) -> None:
    sys.stdout.write("\nГипотезы SPEC раздел 6\n")
    for line in hypothesis_lines(aggregates):
        sys.stdout.write("  " + line + "\n")


def gate_failed(aggregates: Dict[str, Dict[str, Any]]) -> Optional[str]:
    mono = aggregates.get(stages_spec.MODE_MONOLITHIC)
    multi = aggregates.get(stages_spec.MODE_MULTISTAGE)
    if mono is None or multi is None:
        return None
    if multi["missed_emergency_worst"] > mono["missed_emergency_worst"]:
        return (
            "цепочка пропускает больше экстренных случаев: %d против %d по худшему прогону"
            % (multi["missed_emergency_worst"], mono["missed_emergency_worst"])
        )
    return None


def write_report(path: str, payload: Dict[str, Any]) -> None:
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    case_list: List[Dict[str, Any]] = []
    for path in args.cases_paths:
        try:
            case_list.extend(run_eval.load_cases(path, 0))
        except run_eval.CasesError as cases_error:
            sys.stderr.write("Не могу прочитать кейсы: %s\n" % cases_error)
            return stages_spec.EXIT_DATA_ERROR
    cases = {str(case.get("id")): case for case in case_list}

    paths = collect_paths(args.runs)
    if not paths:
        sys.stderr.write(
            "Не найдено ни одного файла прогона в %s. Ожидаются имена вида %s.\n"
            % (
                ", ".join(args.runs),
                ", ".join(
                    mode + stages_spec.RUNS_FILE_SUFFIX + stages_spec.RUNS_FILE_EXTENSION
                    for mode in stages_spec.MODES
                ),
            )
        )
        return stages_spec.EXIT_DATA_ERROR

    runs_by_mode: Dict[str, List[Dict[str, Any]]] = {}
    for mode, path in paths:
        try:
            records = read_records(path)
        except (OSError, ValueError) as read_error:
            sys.stderr.write("Файл %s не читается: %s\n" % (path, read_error))
            return stages_spec.EXIT_DATA_ERROR
        if not records:
            continue
        runs_by_mode.setdefault(mode, []).append(summarize_run(records, cases, mode, path))

    if not runs_by_mode:
        sys.stderr.write("Файлы прогонов пусты.\n")
        return stages_spec.EXIT_DATA_ERROR

    aggregates = {mode: aggregate_mode(mode, runs) for mode, runs in runs_by_mode.items()}
    for mode, runs in runs_by_mode.items():
        sizes = sorted({run["total"] for run in runs})
        if len(sizes) > 1:
            sys.stdout.write(
                "ВНИМАНИЕ: прогоны варианта %s сняты на разном числе кейсов (%s). "
                "Сводить их в один диапазон нельзя, уберите лишние файлы из %s.\n"
                % (mode, ", ".join(str(size) for size in sizes), ", ".join(args.runs))
            )

    sys.stdout.write(
        "Кейсов в наборе: %d, файлы %s\n" % (len(case_list), ", ".join(args.cases_paths))
    )
    for mode in stages_spec.MODES:
        aggregate = aggregates.get(mode)
        if aggregate is None:
            sys.stdout.write("%-12s прогонов нет\n" % mode)
            continue
        sys.stdout.write(
            "%-12s %s, прогонов %d: %s\n"
            % (mode, MODE_TITLES[mode], aggregate["runs"], ", ".join(aggregate["files"]))
        )

    print_main_table(aggregates)
    print_groups(aggregates)
    print_failures(aggregates)
    print_tokens(aggregates)
    print_hypotheses(aggregates)

    problem = gate_failed(aggregates)
    sys.stdout.write("\nГейт\n")
    if problem is None:
        sys.stdout.write("  пройден: цепочка не пропускает экстренных случаев больше монолита\n")
    else:
        sys.stdout.write("  ПРОВАЛЕН: %s\n" % problem)

    payload = {
        "cases_paths": args.cases_paths,
        "cases": len(case_list),
        "modes": aggregates,
        "runs": {mode: runs for mode, runs in runs_by_mode.items()},
        "hypotheses": hypothesis_lines(aggregates),
        "gate_failed": problem,
    }
    write_report(args.out_path, payload)
    sys.stdout.write("\nОтчёт записан: %s\n" % args.out_path)
    return stages_spec.EXIT_GATE_FAILED if problem else stages_spec.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
