"""Сводка по прогонам роутера: метрики из SPEC раздел 5 плюс польза эскалации.

На вход - файлы прогонов router_*.jsonl либо каталог с ними, на выход results/routing_report.json
и таблица в консоль. Кейсы с expected_status = FAIL из подсчёта точности исключаются, как в task7.

Если стратегия прогонялась несколько раз, показывается диапазон и медиана, а для missed_emergency
берётся худший прогон - правило task7, разброс не сглаживается.

Exit code 1, если у любой роутинг-стратегии missed_emergency хуже, чем у only_strong.
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

import router_spec

sys.path.insert(0, router_spec.TASK7_HARNESS_DIR)

import report
import spec7

TABLE_COLUMNS = (
    ("стратегия", 14),
    ("прогонов", 8),
    ("эскал.", 8),
    ("точность", 9),
    ("проп.экс", 8),
    ("ложн.экс", 8),
    ("цена USD", 10),
    ("экономия", 9),
    ("p50 мс", 8),
    ("p95 мс", 8),
    ("low", 6),
    ("high", 6),
)


class RouterReportError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Сводка по прогонам роутера task8.",
    )
    parser.add_argument("inputs", nargs="*", default=[])
    parser.add_argument("--cases", dest="cases_path", default=router_spec.CASES_PATH)
    parser.add_argument("--out", dest="out_path", default=router_spec.DEFAULT_REPORT_PATH)
    return parser


def collect_paths(inputs: List[str]) -> List[str]:
    if not inputs:
        inputs = [router_spec.RAW_DIR]
    paths: List[str] = []
    for entry in inputs:
        if os.path.isdir(entry):
            for name in sorted(os.listdir(entry)):
                if not name.startswith(router_spec.ROUTER_FILE_PREFIX):
                    continue
                if not name.endswith(router_spec.ROUTER_FILE_EXTENSION):
                    continue
                paths.append(os.path.join(entry, name))
            continue
        if not os.path.isfile(entry):
            raise RouterReportError("файл или каталог не найден: %s" % entry)
        paths.append(entry)
    if not paths:
        raise RouterReportError(
            "не нашёл ни одного файла %s*%s - укажите файлы прогонов явно"
            % (router_spec.ROUTER_FILE_PREFIX, router_spec.ROUTER_FILE_EXTENSION)
        )
    return paths


def strategy_of(records: List[Dict[str, Any]], path: str) -> str:
    names = {str(record.get("strategy")) for record in records if record.get("strategy")}
    if len(names) == 1:
        return names.pop()
    if not names:
        raise RouterReportError("в %s нет поля strategy ни в одной записи" % path)
    raise RouterReportError("в %s смешаны стратегии: %s" % (path, ", ".join(sorted(names))))


def route_of_decision(decision: Any) -> Optional[str]:
    if not isinstance(decision, dict):
        return None
    route = decision.get("route")
    if not isinstance(route, str):
        return None
    return route


def counterfactual_routes(runs: List[Dict[str, Any]]) -> Dict[str, str]:
    votes: Dict[str, List[str]] = {}
    for run in runs:
        if run["strategy"] != router_spec.STRATEGY_ONLY_CHEAP:
            continue
        for record in run["records"]:
            route = record.get("final_route")
            if not isinstance(route, str):
                continue
            votes.setdefault(str(record.get("case_id")), []).append(route)
    resolved: Dict[str, str] = {}
    for case_id, routes in votes.items():
        resolved[case_id] = max(routes, key=lambda value: (routes.count(value), -routes.index(value)))
    return resolved


def cheap_route_of(
    record: Dict[str, Any], counterfactual: Dict[str, str]
) -> Tuple[Optional[str], str]:
    paired = route_of_decision(record.get("cheap_decision"))
    if paired is not None:
        return paired, router_spec.BENEFIT_SOURCE_PAIR
    fallback = counterfactual.get(str(record.get("case_id")))
    if fallback is not None:
        return fallback, router_spec.BENEFIT_SOURCE_COUNTERFACTUAL
    return None, router_spec.BENEFIT_SOURCE_NONE


def empty_benefit() -> Dict[str, Any]:
    return {
        "escalated": 0,
        "comparable": 0,
        "from_pair": 0,
        "from_counterfactual": 0,
        "not_comparable": 0,
        "changed_route": 0,
        "unchanged_route": 0,
        "improved": 0,
        "worsened": 0,
        "neutral_change": 0,
        "emergency_rescued": 0,
        "emergency_lost": 0,
        "wasted_calls": 0,
    }


def escalation_benefit(
    records: List[Dict[str, Any]],
    cases: Dict[str, Dict[str, Any]],
    counterfactual: Dict[str, str],
) -> Dict[str, Any]:
    benefit = empty_benefit()
    for record in records:
        if not record.get("escalated"):
            continue
        benefit["escalated"] += 1
        strong_route = route_of_decision(record.get("strong_decision"))
        cheap_route, source = cheap_route_of(record, counterfactual)
        if source == router_spec.BENEFIT_SOURCE_PAIR:
            benefit["from_pair"] += 1
        elif source == router_spec.BENEFIT_SOURCE_COUNTERFACTUAL:
            benefit["from_counterfactual"] += 1
        case = cases.get(str(record.get("case_id")))
        if cheap_route is None or case is None or report.expects_fail(case):
            benefit["not_comparable"] += 1
            continue
        benefit["comparable"] += 1
        if strong_route == cheap_route:
            benefit["unchanged_route"] += 1
            benefit["wasted_calls"] += 1
            continue
        benefit["changed_route"] += 1
        gold = str(case.get("expected_route"))
        if strong_route == gold and cheap_route != gold:
            benefit["improved"] += 1
        elif cheap_route == gold and strong_route != gold:
            benefit["worsened"] += 1
        else:
            benefit["neutral_change"] += 1
        cheap_missed = gold == spec7.ROUTE_EMERGENCY and report.route_severity(
            cheap_route
        ) < spec7.SEVERITY[spec7.ROUTE_EMERGENCY]
        strong_missed = gold == spec7.ROUTE_EMERGENCY and report.route_severity(
            strong_route
        ) < spec7.SEVERITY[spec7.ROUTE_EMERGENCY]
        if cheap_missed and not strong_missed:
            benefit["emergency_rescued"] += 1
        if strong_missed and not cheap_missed:
            benefit["emergency_lost"] += 1
    return benefit


def count_reasons(records: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for record in records:
        for code in record.get("escalation_reasons") or []:
            counts[str(code)] = counts.get(str(code), 0) + 1
    ordered: Dict[str, int] = {}
    for code in router_spec.ESCALATION_CODES:
        if code in counts:
            ordered[code] = counts[code]
    for code in sorted(counts):
        if code not in ordered:
            ordered[code] = counts[code]
    return ordered


def summarize_run(
    records: List[Dict[str, Any]],
    cases: Dict[str, Dict[str, Any]],
    strategy: str,
    path: str,
    counterfactual: Dict[str, str],
) -> Dict[str, Any]:
    route_graded = 0
    correct = 0
    missed_emergency = 0
    false_emergency = 0
    status_graded = 0
    status_correct = 0
    escalated = 0
    errors = 0
    unknown_cases = 0
    calls_cheap = 0
    calls_strong = 0
    cost = 0.0
    latencies: List[float] = []

    for record in records:
        if record.get("escalated"):
            escalated += 1
        if record.get("error"):
            errors += 1
        calls_cheap += int(record.get("calls_cheap") or 0)
        calls_strong += int(record.get("calls_strong") or 0)
        value = record.get("cost_usd")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            cost += float(value)
        latency = record.get("latency_ms")
        if isinstance(latency, int):
            latencies.append(float(latency))
        case = cases.get(str(record.get("case_id")))
        if case is None:
            unknown_cases += 1
            continue
        if report.expects_fail(case):
            status_graded += 1
            if record.get("final_status") == spec7.STATUS_FAIL:
                status_correct += 1
            continue
        gold = str(case.get("expected_route"))
        predicted = record.get("final_route")
        route_graded += 1
        if predicted == gold:
            correct += 1
        if gold == spec7.ROUTE_EMERGENCY and report.route_severity(predicted) < spec7.SEVERITY[gold]:
            missed_emergency += 1
        if gold != spec7.ROUTE_EMERGENCY and predicted == spec7.ROUTE_EMERGENCY:
            false_emergency += 1

    total = len(records)
    return {
        "strategy": strategy,
        "path": path,
        "file": os.path.basename(path),
        "total": total,
        "escalated": escalated,
        "stayed": total - escalated,
        "escalated_share": round(escalated / total, 4) if total else 0.0,
        "stayed_share": round((total - escalated) / total, 4) if total else 0.0,
        "route_graded": route_graded,
        "correct": correct,
        "accuracy": round(correct / route_graded, 4) if route_graded else 0.0,
        "missed_emergency": missed_emergency,
        "false_emergency": false_emergency,
        "noisy_expected_fail": status_graded,
        "noisy_handled": status_correct,
        "calls_cheap": calls_cheap,
        "calls_strong": calls_strong,
        "cost_usd": round(cost, 6),
        "latency_p50_ms": int(report.percentile(latencies, router_spec.PERCENTILE_50)),
        "latency_p95_ms": int(report.percentile(latencies, router_spec.PERCENTILE_95)),
        "errors": errors,
        "unknown_cases": unknown_cases,
        "escalation_reasons": count_reasons(records),
        "benefit": escalation_benefit(records, cases, counterfactual),
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


def merge_reasons(runs: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for run in runs:
        for code, value in run["escalation_reasons"].items():
            counts[code] = counts.get(code, 0) + value
    ordered: Dict[str, int] = {}
    for code in router_spec.ESCALATION_CODES:
        if code in counts:
            ordered[code] = counts[code]
    for code in sorted(counts):
        if code not in ordered:
            ordered[code] = counts[code]
    return ordered


def merge_benefit(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = empty_benefit()
    for run in runs:
        for key, value in run["benefit"].items():
            total[key] = total.get(key, 0) + value
    return total


def aggregate_strategy(strategy: str, runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "strategy": strategy,
        "title": router_spec.STRATEGY_TITLES.get(strategy, strategy),
        "runs": len(runs),
        "files": [run["file"] for run in runs],
        "total": runs[0]["total"],
        "escalated_share": spread([run["escalated_share"] for run in runs]),
        "stayed_share": spread([run["stayed_share"] for run in runs]),
        "accuracy": spread([run["accuracy"] for run in runs]),
        "missed_emergency": spread([float(run["missed_emergency"]) for run in runs], True),
        "missed_emergency_worst": max(run["missed_emergency"] for run in runs),
        "false_emergency": spread([float(run["false_emergency"]) for run in runs], True),
        "false_emergency_worst": max(run["false_emergency"] for run in runs),
        "cost_usd": spread([run["cost_usd"] for run in runs]),
        "calls_cheap": spread([float(run["calls_cheap"]) for run in runs], True),
        "calls_strong": spread([float(run["calls_strong"]) for run in runs], True),
        "latency_p50_ms": spread([float(run["latency_p50_ms"]) for run in runs], True),
        "latency_p95_ms": spread([float(run["latency_p95_ms"]) for run in runs], True),
        "errors": sum(run["errors"] for run in runs),
        "noisy_handled": spread([float(run["noisy_handled"]) for run in runs], True),
        "escalation_reasons": merge_reasons(runs),
        "benefit": merge_benefit(runs),
        "saved_vs_strong_usd": None,
        "saved_vs_strong_share": None,
    }


def apply_savings(aggregates: Dict[str, Dict[str, Any]]) -> Optional[float]:
    strong = aggregates.get(router_spec.STRATEGY_ONLY_STRONG)
    if strong is None:
        return None
    reference = strong["cost_usd"]["median"]
    for aggregate in aggregates.values():
        saved = reference - aggregate["cost_usd"]["median"]
        aggregate["saved_vs_strong_usd"] = round(saved, 6)
        if reference > 0:
            aggregate["saved_vs_strong_share"] = round(saved / reference, 4)
    return reference


def gate_failures(aggregates: Dict[str, Dict[str, Any]]) -> List[str]:
    strong = aggregates.get(router_spec.STRATEGY_ONLY_STRONG)
    if strong is None:
        return []
    limit = strong["missed_emergency_worst"]
    failures = []
    for strategy in router_spec.ROUTING_STRATEGIES:
        aggregate = aggregates.get(strategy)
        if aggregate is None:
            continue
        if aggregate["missed_emergency_worst"] > limit:
            failures.append(
                "%s: пропущено экстренных %d против %d у %s"
                % (
                    strategy,
                    aggregate["missed_emergency_worst"],
                    limit,
                    router_spec.STRATEGY_ONLY_STRONG,
                )
            )
    return failures


def format_share(value: Any) -> str:
    if value is None:
        return router_spec.NOT_AVAILABLE
    return "%.0f%%" % (float(value) * 100)


def format_cost(value: float) -> str:
    if value == 0:
        return "0"
    return "%.6f" % value


def value_with_spread(block: Dict[str, Any], formatter) -> str:
    if block["min"] == block["max"]:
        return formatter(block["median"])
    return "%s (%s..%s)" % (
        formatter(block["median"]),
        formatter(block["min"]),
        formatter(block["max"]),
    )


def print_table(aggregates: Dict[str, Dict[str, Any]]) -> None:
    header = " ".join("%-*s" % (width, title) for title, width in TABLE_COLUMNS)
    sys.stdout.write("\nСводка по стратегиям\n")
    sys.stdout.write(header + "\n")
    sys.stdout.write("-" * len(header) + "\n")
    for strategy in router_spec.STRATEGIES:
        aggregate = aggregates.get(strategy)
        if aggregate is None:
            continue
        cells = (
            strategy,
            str(aggregate["runs"]),
            format_share(aggregate["escalated_share"]["median"]),
            "%.4f" % aggregate["accuracy"]["median"],
            str(aggregate["missed_emergency_worst"]),
            str(aggregate["false_emergency_worst"]),
            format_cost(aggregate["cost_usd"]["median"]),
            format_share(aggregate["saved_vs_strong_share"]),
            str(aggregate["latency_p50_ms"]["median"]),
            str(aggregate["latency_p95_ms"]["median"]),
            str(aggregate["calls_cheap"]["median"]),
            str(aggregate["calls_strong"]["median"]),
        )
        sys.stdout.write(
            " ".join("%-*s" % (width, cell) for cell, (_, width) in zip(cells, TABLE_COLUMNS))
            + "\n"
        )
    sys.stdout.write(
        "\nпроп.экс и ложн.экс - худший прогон, остальное - медиана по прогонам. "
        "low и high - вызовы дешёвого и сильного уровня.\n"
    )


def print_spreads(aggregates: Dict[str, Dict[str, Any]]) -> None:
    sys.stdout.write("\nРазброс между прогонами\n")
    for strategy in router_spec.STRATEGIES:
        aggregate = aggregates.get(strategy)
        if aggregate is None:
            continue
        sys.stdout.write(
            "  %-14s точность %s, пропущено экстренных %s, цена %s\n"
            % (
                strategy,
                value_with_spread(aggregate["accuracy"], lambda value: "%.4f" % value),
                value_with_spread(aggregate["missed_emergency"], lambda value: str(int(value))),
                value_with_spread(aggregate["cost_usd"], format_cost),
            )
        )


def print_reasons(aggregates: Dict[str, Dict[str, Any]]) -> None:
    sys.stdout.write("\nСрабатывания эвристик, суммарно по прогонам\n")
    for strategy in router_spec.STRATEGIES:
        aggregate = aggregates.get(strategy)
        if aggregate is None:
            continue
        reasons = aggregate["escalation_reasons"]
        if not reasons:
            sys.stdout.write("  %-14s эвристики не срабатывали\n" % strategy)
            continue
        parts = ["%s %d" % (code, count) for code, count in reasons.items()]
        sys.stdout.write("  %-14s %s\n" % (strategy, ", ".join(parts)))


def print_benefit(aggregates: Dict[str, Dict[str, Any]]) -> None:
    sys.stdout.write("\nПольза эскалации, суммарно по прогонам\n")
    for strategy in router_spec.ROUTING_STRATEGIES:
        aggregate = aggregates.get(strategy)
        if aggregate is None:
            continue
        benefit = aggregate["benefit"]
        sys.stdout.write(
            "  %-14s эскалировано %d, сравнимо %d, маршрут поменялся %d, "
            "стало точнее %d, стало хуже %d, впустую %d\n"
            % (
                strategy,
                benefit["escalated"],
                benefit["comparable"],
                benefit["changed_route"],
                benefit["improved"],
                benefit["worsened"],
                benefit["wasted_calls"],
            )
        )
        if benefit["emergency_rescued"] or benefit["emergency_lost"]:
            sys.stdout.write(
                "                 экстренных спасено %d, потеряно %d\n"
                % (benefit["emergency_rescued"], benefit["emergency_lost"])
            )
        if benefit["from_counterfactual"]:
            sys.stdout.write(
                "                 из них %d сравнены с прогоном %s: дешёвый уровень не вызывался\n"
                % (benefit["from_counterfactual"], router_spec.STRATEGY_ONLY_CHEAP)
            )
        if benefit["not_comparable"]:
            sys.stdout.write(
                "                 не с чем сравнить %d\n" % benefit["not_comparable"]
            )


def print_success_criteria(aggregates: Dict[str, Dict[str, Any]]) -> None:
    cheap = aggregates.get(router_spec.STRATEGY_ONLY_CHEAP)
    strong = aggregates.get(router_spec.STRATEGY_ONLY_STRONG)
    if cheap is None or strong is None:
        sys.stdout.write(
            "\nКритерий успеха не проверить: нужны прогоны %s и %s.\n"
            % (router_spec.STRATEGY_ONLY_CHEAP, router_spec.STRATEGY_ONLY_STRONG)
        )
        return
    sys.stdout.write("\nКритерий успеха из SPEC раздел 7\n")
    for strategy in router_spec.ROUTING_STRATEGIES:
        aggregate = aggregates.get(strategy)
        if aggregate is None:
            continue
        safe = aggregate["missed_emergency_worst"] <= strong["missed_emergency_worst"]
        accurate = aggregate["accuracy"]["median"] >= cheap["accuracy"]["median"]
        cheaper = aggregate["cost_usd"]["median"] < strong["cost_usd"]["median"]
        sys.stdout.write(
            "  %-14s безопасность %s, точность %s, цена %s -> %s\n"
            % (
                strategy,
                "да" if safe else "нет",
                "да" if accurate else "нет",
                "да" if cheaper else "нет",
                "удался" if safe and accurate and cheaper else "не удался",
            )
        )


def write_report(path: str, payload: Dict[str, Any]) -> None:
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = collect_paths(args.inputs)
        cases = report.load_cases(args.cases_path)
        runs = []
        for path in paths:
            records = report.read_jsonl(path)
            runs.append(
                {"path": path, "strategy": strategy_of(records, path), "records": records}
            )
    except (RouterReportError, report.ReportInputError) as input_error:
        sys.stderr.write("Не могу собрать сводку: %s\n" % input_error)
        return router_spec.EXIT_DATA_ERROR
    except OSError as os_error:
        sys.stderr.write("Ошибка чтения: %s\n" % os_error)
        return router_spec.EXIT_DATA_ERROR

    counterfactual = counterfactual_routes(runs)
    summaries = [
        summarize_run(run["records"], cases, run["strategy"], run["path"], counterfactual)
        for run in runs
    ]

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for summary in summaries:
        grouped.setdefault(summary["strategy"], []).append(summary)

    aggregates = {
        strategy: aggregate_strategy(strategy, group) for strategy, group in grouped.items()
    }
    reference_cost = apply_savings(aggregates)
    failures = gate_failures(aggregates)

    sys.stdout.write("Прогонов прочитано: %d\n" % len(summaries))
    sys.stdout.write("Кейсов в наборе: %d, файл %s\n" % (len(cases), args.cases_path))
    if reference_cost is None:
        sys.stdout.write(
            "Прогона %s нет, экономия и гейт по безопасности не считаются.\n"
            % router_spec.STRATEGY_ONLY_STRONG
        )

    print_table(aggregates)
    print_spreads(aggregates)
    print_reasons(aggregates)
    print_benefit(aggregates)
    print_success_criteria(aggregates)

    payload = {
        "cases_path": args.cases_path,
        "cases_total": len(cases),
        "confidence_thresholds": list(router_spec.CONFIDENCE_THRESHOLDS),
        "answer_length_bounds": [router_spec.MIN_ANSWER_CHARS, router_spec.MAX_ANSWER_CHARS],
        "reference_cost_usd": reference_cost,
        "strategies": {
            strategy: aggregates[strategy]
            for strategy in router_spec.STRATEGIES
            if strategy in aggregates
        },
        "runs": summaries,
        "gate_failures": failures,
    }
    write_report(args.out_path, payload)
    sys.stdout.write("\nОтчёт записан: %s\n" % args.out_path)

    if failures:
        sys.stderr.write("\nГейт безопасности не пройден:\n")
        for failure in failures:
            sys.stderr.write("  %s\n" % failure)
        return router_spec.EXIT_GATE_FAILED
    return router_spec.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
