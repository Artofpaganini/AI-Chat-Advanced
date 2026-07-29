"""Сводка по прогонам: метрики SPEC раздел 8 для baseline и pipeline рядом.

Кейсы с expected_status = FAIL судятся по статусу, а не по маршруту: это метрика noisy_handled.
Exit code 1, если у pipeline missed_emergency больше нуля - это блокирующая метрика.

Если критик работал на другой модели, в сводке видно обе: основную и критика, и деньги разбиты
на две строки. В JSON у каждой модели свой блок цены, поле cost_usd внутри блока - это доля
именно этой модели, общая сумма лежит в cost_usd_total.

Запуск: python3 harness/report.py
        python3 harness/report.py --baseline raw/baseline_runs.jsonl --pipeline raw/pipeline_runs.jsonl
"""

import argparse
import json
import os
import statistics
import sys
from typing import Any, Dict, List, Optional

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import llm_client
import pipeline
import spec7

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_DATA_ERROR = 2
PERCENTILE_50 = 0.5
PERCENTILE_95 = 0.95
NO_ROUTE = "NONE"
MODEL_ABSENT = "не записано в артефакте"
CRITIC_ABSENT = "критик не участвовал"
PRICE_SOURCE_ABSENT = ""
TRIGGER_ABSENT = "не записан в артефакте"
TABLE_WIDTH = 88


class ReportInputError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Сравнение baseline и полного цикла: точность, пропуски, отказы, цена.",
    )
    parser.add_argument(
        "--baseline",
        dest="baseline_path",
        default=os.path.join(spec7.RAW_DIR, spec7.BASELINE_RUNS_NAME),
    )
    parser.add_argument(
        "--pipeline",
        dest="pipeline_path",
        default=os.path.join(spec7.RAW_DIR, spec7.PIPELINE_RUNS_NAME),
    )
    parser.add_argument("--cases", dest="cases_path", default=spec7.DEFAULT_CASES_PATH)
    parser.add_argument("--out", dest="out_path", default=spec7.DEFAULT_REPORT_PATH)
    return parser


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        raise ReportInputError("файл не найден: %s" % path)
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except ValueError as parse_error:
                raise ReportInputError(
                    "строка %d в %s не парсится как JSON: %s" % (line_number, path, parse_error)
                )
            if not isinstance(payload, dict):
                raise ReportInputError("строка %d в %s не объект JSON" % (line_number, path))
            records.append(payload)
    if not records:
        raise ReportInputError("файл пустой: %s" % path)
    return records


def load_cases(path: str) -> Dict[str, Dict[str, Any]]:
    cases = {}
    for payload in read_jsonl(path):
        case_id = payload.get("id")
        if not isinstance(case_id, str):
            raise ReportInputError("в %s есть кейс без строкового id" % path)
        cases[case_id] = payload
    return cases


def percentile(values: List[float], share: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = int(share * len(ordered))
    if share * len(ordered) > rank:
        rank += 1
    if rank < 1:
        rank = 1
    return float(ordered[rank - 1])


def expects_fail(case: Dict[str, Any]) -> bool:
    return case.get("expected_status") == spec7.STATUS_FAIL


def route_severity(route: Optional[str]) -> int:
    if route not in spec7.SEVERITY:
        return -1
    return spec7.SEVERITY[route]


def count_violations(records: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for record in records:
        violations = record.get("violations") or []
        for code in violations:
            counts[str(code)] = counts.get(str(code), 0) + 1
    ordered = {}
    for code in spec7.ALL_CODES:
        if code in counts:
            ordered[code] = counts[code]
    for code in sorted(counts):
        if code not in ordered:
            ordered[code] = counts[code]
    return ordered


def confusion_matrix(
    records: List[Dict[str, Any]], cases: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, int]]:
    matrix: Dict[str, Dict[str, int]] = {}
    for record in records:
        case = cases.get(str(record.get("case_id")))
        if case is None or expects_fail(case):
            continue
        gold = str(case.get("expected_route"))
        predicted = record.get("route") or NO_ROUTE
        row = matrix.setdefault(gold, {})
        row[predicted] = row.get(predicted, 0) + 1
    return matrix


def group_breakdown(
    records: List[Dict[str, Any]], cases: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    breakdown: Dict[str, Dict[str, Any]] = {}
    for record in records:
        case = cases.get(str(record.get("case_id")))
        if case is None:
            continue
        group = str(case.get("group", "-"))
        bucket = breakdown.setdefault(
            group,
            {
                "total": 0,
                "route_graded": 0,
                "correct": 0,
                "accuracy": 0.0,
                "missed_emergency": 0,
                "false_emergency": 0,
                "status_graded": 0,
                "status_correct": 0,
                "rejected": 0,
                "unsure": 0,
            },
        )
        bucket["total"] += 1
        if record.get("status") == spec7.STATUS_FAIL:
            bucket["rejected"] += 1
        if record.get("status") == spec7.STATUS_UNSURE:
            bucket["unsure"] += 1
        if expects_fail(case):
            bucket["status_graded"] += 1
            if record.get("status") == spec7.STATUS_FAIL:
                bucket["status_correct"] += 1
            continue
        gold = str(case.get("expected_route"))
        predicted = record.get("route")
        bucket["route_graded"] += 1
        if predicted == gold:
            bucket["correct"] += 1
        if gold == spec7.ROUTE_EMERGENCY and route_severity(predicted) < spec7.SEVERITY[gold]:
            bucket["missed_emergency"] += 1
        if gold != spec7.ROUTE_EMERGENCY and predicted == spec7.ROUTE_EMERGENCY:
            bucket["false_emergency"] += 1
    for bucket in breakdown.values():
        if bucket["route_graded"]:
            bucket["accuracy"] = round(bucket["correct"] / bucket["route_graded"], 4)
    return breakdown


def markers_of(record: Dict[str, Any], case: Optional[Dict[str, Any]]) -> List[str]:
    recorded = record.get("risk_markers")
    if isinstance(recorded, list):
        return [str(label) for label in recorded]
    if case is None:
        return []
    return pipeline.detect_risk_markers(str(case.get("text", "")))


def dominant_location(locations: Dict[str, int]) -> str:
    if not locations:
        return spec7.LOCATION_CLOUD
    return max(locations.items(), key=lambda item: item[1])[0]


def describe_cost(summary: Dict[str, Any]) -> str:
    if summary.get("inference_location") == spec7.LOCATION_LOCAL:
        return "локально, деньги не тратятся"
    if summary.get("price_source") == spec7.PRICE_SOURCE_UNKNOWN:
        return "цена не подтверждена"
    return "%.4f" % summary["cost_usd"]


def describe_main_cost(summary: Dict[str, Any]) -> str:
    if summary.get("inference_location") == spec7.LOCATION_LOCAL:
        return "локально, деньги не тратятся"
    if summary.get("price_source") == spec7.PRICE_SOURCE_UNKNOWN:
        return "цена не подтверждена"
    return "%.4f" % float(summary.get("main_cost_usd") or 0.0)


def order_markers(counts: Dict[str, int]) -> Dict[str, int]:
    ordered: Dict[str, int] = {}
    for label in spec7.RISK_LABELS:
        if label in counts:
            ordered[label] = counts[label]
    for label in sorted(counts):
        if label not in ordered:
            ordered[label] = counts[label]
    return ordered


def dominant_value(values: Dict[str, int], fallback: str) -> str:
    if not values:
        return fallback
    return max(values.items(), key=lambda item: item[1])[0]


def describe_price_source(summary: Dict[str, Any]) -> str:
    source = summary.get("price_source")
    if not source:
        return "не записан в артефакте"
    if source == spec7.PRICE_SOURCE_LOCAL:
        return "локально, тариф не нужен"
    if source == spec7.PRICE_SOURCE_UNKNOWN:
        return "не подтверждён"
    return str(source)


def describe_tariff(summary: Dict[str, Any]) -> str:
    if summary.get("inference_location") == spec7.LOCATION_LOCAL:
        return "не нужен"
    price = llm_client.resolve_price(str(summary.get("model") or ""))
    if price["source"] == spec7.PRICE_SOURCE_UNKNOWN:
        return "не найден"
    return price["resolved_as"]


def critic_took_part(summary: Dict[str, Any]) -> bool:
    model = str(summary.get("critic_model") or "")
    return bool(model) and model != CRITIC_ABSENT


def describe_critic_model(summary: Dict[str, Any]) -> str:
    if not critic_took_part(summary):
        return CRITIC_ABSENT
    return str(summary.get("critic_model"))


def describe_critic_tariff(summary: Dict[str, Any]) -> str:
    if not critic_took_part(summary):
        return "не нужен"
    if summary.get("critic_inference_location") == spec7.LOCATION_LOCAL:
        return "не нужен"
    price = llm_client.resolve_price(str(summary.get("critic_model") or ""))
    if price["source"] == spec7.PRICE_SOURCE_UNKNOWN:
        return "не найден"
    return price["resolved_as"]


def describe_critic_cost(summary: Dict[str, Any]) -> str:
    if not critic_took_part(summary):
        return "-"
    if summary.get("critic_inference_location") == spec7.LOCATION_LOCAL:
        return "локально, деньги не тратятся"
    if summary.get("critic_price_source") == spec7.PRICE_SOURCE_UNKNOWN:
        return "цена не подтверждена"
    return "%.4f" % float(summary.get("critic_cost_usd") or 0.0)


def price_entry(model: str, price_source: Any, cost: Any) -> Dict[str, Any]:
    price = llm_client.resolve_price(model)
    return {
        "model": model or MODEL_ABSENT,
        "price_source": price_source,
        "resolved_as": price["resolved_as"],
        "input_per_mtok": price["input"],
        "cached_input_per_mtok": price["cached_input"],
        "output_per_mtok": price["output"],
        "source_url": price["source_url"],
        "note": price["note"],
        "cost_usd": cost,
        "cost_confirmed": price_source != spec7.PRICE_SOURCE_UNKNOWN,
    }


def price_block(summaries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    block = {}
    for mode, summary in summaries.items():
        entry = price_entry(
            str(summary.get("model") or ""),
            summary.get("price_source"),
            summary.get("main_cost_usd"),
        )
        entry["cost_usd_total"] = summary.get("cost_usd")
        if critic_took_part(summary):
            entry["critic"] = price_entry(
                str(summary.get("critic_model") or ""),
                summary.get("critic_price_source"),
                summary.get("critic_cost_usd"),
            )
        else:
            entry["critic"] = {"model": CRITIC_ABSENT, "cost_usd": 0.0}
        block[mode] = entry
    return block


def sum_field(records: List[Dict[str, Any]], holder: str, key: str) -> int:
    total = 0
    for record in records:
        payload = record.get(holder) or {}
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            continue
        total += value
    return total


def summarize(
    records: List[Dict[str, Any]], cases: Dict[str, Dict[str, Any]], mode: str
) -> Dict[str, Any]:
    route_graded = 0
    correct = 0
    missed_emergency = 0
    false_emergency = 0
    status_graded = 0
    status_correct = 0
    rejected = 0
    unsure = 0
    ok_status = 0
    retried = 0
    extra_calls = 0
    total_calls = 0
    escalated = 0
    self_check_ran = 0
    risk_missed = 0
    risk_cases = 0
    risk_marker_counts: Dict[str, int] = {}
    triggers: Dict[str, int] = {}
    errors = 0
    unknown_cases = 0
    input_rejected = 0
    input_violations = 0
    locations: Dict[str, int] = {}
    models: Dict[str, int] = {}
    price_sources: Dict[str, int] = {}
    critic_models: Dict[str, int] = {}
    critic_locations: Dict[str, int] = {}
    critic_price_sources: Dict[str, int] = {}
    latencies: List[float] = []
    confidences: List[float] = []

    for record in records:
        location = str(record.get("inference_location") or spec7.LOCATION_CLOUD)
        locations[location] = locations.get(location, 0) + 1
        model_name = str(record.get("model") or "")
        if model_name:
            models[model_name] = models.get(model_name, 0) + 1
        source_name = str(record.get("price_source") or "")
        if source_name:
            price_sources[source_name] = price_sources.get(source_name, 0) + 1
        critic_name = str(record.get("critic_model") or "")
        if critic_name:
            critic_models[critic_name] = critic_models.get(critic_name, 0) + 1
        critic_location = str(record.get("critic_inference_location") or "")
        if critic_location:
            critic_locations[critic_location] = critic_locations.get(critic_location, 0) + 1
        critic_source = str(record.get("critic_price_source") or "")
        if critic_source:
            critic_price_sources[critic_source] = critic_price_sources.get(critic_source, 0) + 1
        if record.get("input_rejected"):
            input_rejected += 1
        if any(code in spec7.INPUT_CODES for code in record.get("violations") or []):
            input_violations += 1
        case = cases.get(str(record.get("case_id")))
        trigger_name = str(record.get("self_check_trigger") or "")
        if trigger_name:
            triggers[trigger_name] = triggers.get(trigger_name, 0) + 1
        markers = markers_of(record, case)
        if markers:
            risk_cases += 1
            for label in markers:
                risk_marker_counts[label] = risk_marker_counts.get(label, 0) + 1
        latency = record.get("latency_ms")
        if isinstance(latency, int):
            latencies.append(float(latency))
        confidence = record.get("confidence_final")
        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
            confidences.append(float(confidence))
        calls = record.get("calls") if isinstance(record.get("calls"), int) else 0
        total_calls += calls
        extra_calls += max(0, calls - 1)
        if record.get("retried"):
            retried += 1
        if record.get("escalated_by_safety"):
            escalated += 1
        if record.get("self_check_ran"):
            self_check_ran += 1
        if record.get("risk_missed"):
            risk_missed += 1
        if record.get("error"):
            errors += 1
        status = record.get("status")
        if status == spec7.STATUS_FAIL:
            rejected += 1
        elif status == spec7.STATUS_UNSURE:
            unsure += 1
        elif status == spec7.STATUS_OK:
            ok_status += 1
        if case is None:
            unknown_cases += 1
            continue
        if expects_fail(case):
            status_graded += 1
            if status == spec7.STATUS_FAIL:
                status_correct += 1
            continue
        gold = str(case.get("expected_route"))
        predicted = record.get("route")
        route_graded += 1
        if predicted == gold:
            correct += 1
        if gold == spec7.ROUTE_EMERGENCY and route_severity(predicted) < spec7.SEVERITY[gold]:
            missed_emergency += 1
        if gold != spec7.ROUTE_EMERGENCY and predicted == spec7.ROUTE_EMERGENCY:
            false_emergency += 1

    prompt_tokens = sum_field(records, "usage_total", "prompt_tokens")
    completion_tokens = sum_field(records, "usage_total", "completion_tokens")
    critic_prompt_tokens = sum_field(records, "critic_usage_total", "prompt_tokens")
    critic_completion_tokens = sum_field(records, "critic_usage_total", "completion_tokens")
    cost = sum(
        float(record.get("cost_usd") or 0.0)
        for record in records
        if isinstance(record.get("cost_usd"), (int, float))
    )
    critic_cost = sum(
        float(record.get("critic_cost_usd") or 0.0)
        for record in records
        if isinstance(record.get("critic_cost_usd"), (int, float))
    )

    return {
        "mode": mode,
        "total": len(records),
        "route_graded": route_graded,
        "correct": correct,
        "accuracy": round(correct / route_graded, 4) if route_graded else 0.0,
        "missed_emergency": missed_emergency,
        "false_emergency": false_emergency,
        "rejected": rejected,
        "unsure": unsure,
        "ok": ok_status,
        "noisy_handled": status_correct,
        "noisy_expected_fail": status_graded,
        "noisy_handled_share": round(status_correct / status_graded, 4) if status_graded else 0.0,
        "input_rejected": input_rejected,
        "input_violations": input_violations,
        "saved_calls": input_rejected * spec7.REDUNDANCY_SAMPLES,
        "retried": retried,
        "extra_calls": extra_calls,
        "total_calls": total_calls,
        "escalated_by_safety": escalated,
        "self_check_ran": self_check_ran,
        "self_check_trigger": dominant_value(triggers, TRIGGER_ABSENT),
        "risk_cases": risk_cases,
        "risk_markers": order_markers(risk_marker_counts),
        "risk_missed": risk_missed,
        "errors": errors,
        "unknown_cases": unknown_cases,
        "latency_p50_ms": int(percentile(latencies, PERCENTILE_50)),
        "latency_p95_ms": int(percentile(latencies, PERCENTILE_95)),
        "latency_median_ms": int(statistics.median(latencies)) if latencies else 0,
        "confidence_mean": round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "critic_prompt_tokens": critic_prompt_tokens,
        "critic_completion_tokens": critic_completion_tokens,
        "cost_usd": round(cost, 6),
        "critic_cost_usd": round(critic_cost, 6),
        "main_cost_usd": round(cost - critic_cost, 6),
        "inference_location": dominant_location(locations),
        "inference_location_counts": locations,
        "model": dominant_value(models, MODEL_ABSENT),
        "price_source": dominant_value(price_sources, PRICE_SOURCE_ABSENT),
        "critic_model": dominant_value(critic_models, CRITIC_ABSENT),
        "critic_inference_location": dominant_value(critic_locations, PRICE_SOURCE_ABSENT),
        "critic_price_source": dominant_value(critic_price_sources, PRICE_SOURCE_ABSENT),
        "violations": count_violations(records),
        "groups": group_breakdown(records, cases),
        "confusion": confusion_matrix(records, cases),
    }


def format_number(value: Any) -> str:
    if isinstance(value, float):
        return "%.4f" % value
    return str(value)


def print_comparison(summaries: Dict[str, Dict[str, Any]]) -> None:
    rows = (
        ("кейсов всего", "total"),
        ("судится по маршруту", "route_graded"),
        ("accuracy", "accuracy"),
        ("missed_emergency", "missed_emergency"),
        ("false_emergency", "false_emergency"),
        ("rejected (FAIL)", "rejected"),
        ("unsure", "unsure"),
        ("ok", "ok"),
        ("noisy_handled", "noisy_handled"),
        ("отказов по предусловию", "input_rejected"),
        ("saved_calls", "saved_calls"),
        ("retried", "retried"),
        ("extra_calls", "extra_calls"),
        ("вызовов всего", "total_calls"),
        ("self_check запусков", "self_check_ran"),
        ("режим триггера критика", "self_check_trigger"),
        ("кейсов с признаком риска", "risk_cases"),
        ("safety-подъёмов", "escalated_by_safety"),
        ("risk_missed", "risk_missed"),
        ("latency p50, мс", "latency_p50_ms"),
        ("latency p95, мс", "latency_p95_ms"),
        ("confidence средняя", "confidence_mean"),
        ("токенов вход", "prompt_tokens"),
        ("токенов выход", "completion_tokens"),
        ("инференс", "inference_location"),
        ("модель", "model"),
        ("источник цены", "price_source"),
        ("тариф", "price_tariff"),
        ("модель критика", "critic_model"),
        ("тариф критика", "critic_price_tariff"),
        ("стоимость основной, USD", "main_cost_usd"),
        ("стоимость критика, USD", "critic_cost_usd"),
        ("стоимость всего, USD", "cost_usd"),
        ("кейсов с ошибкой", "errors"),
    )
    baseline = summaries.get(spec7.MODE_BASELINE)
    controlled = summaries.get(spec7.MODE_PIPELINE)
    sys.stdout.write("\n" + "=" * TABLE_WIDTH + "\n")
    sys.stdout.write("СРАВНЕНИЕ: baseline против полного цикла\n")
    sys.stdout.write("=" * TABLE_WIDTH + "\n")
    sys.stdout.write("%-26s %-29s %-29s\n" % ("метрика", "baseline", "pipeline"))
    sys.stdout.write("-" * TABLE_WIDTH + "\n")
    for title, key in rows:
        left = cell_value(baseline, key)
        right = cell_value(controlled, key)
        sys.stdout.write("%-26s %-29s %-29s\n" % (title, left, right))
    sys.stdout.write("-" * TABLE_WIDTH + "\n")


def cell_value(summary: Optional[Dict[str, Any]], key: str) -> str:
    if summary is None:
        return "-"
    if key == "cost_usd":
        return describe_cost(summary)
    if key == "main_cost_usd":
        return describe_main_cost(summary)
    if key == "critic_cost_usd":
        return describe_critic_cost(summary)
    if key == "price_source":
        return describe_price_source(summary)
    if key == "price_tariff":
        return describe_tariff(summary)
    if key == "critic_model":
        return describe_critic_model(summary)
    if key == "critic_price_tariff":
        return describe_critic_tariff(summary)
    if key == "self_check_trigger":
        return describe_trigger(summary)
    return format_number(summary[key])


def describe_trigger(summary: Dict[str, Any]) -> str:
    trigger = str(summary.get("self_check_trigger") or "")
    if not trigger or trigger == TRIGGER_ABSENT:
        return TRIGGER_ABSENT
    if trigger == spec7.SELF_CHECK_TRIGGER_NONE:
        return "не применяется (baseline)"
    return trigger


def print_violations(summary: Dict[str, Any]) -> None:
    violations = summary.get("violations") or {}
    sys.stdout.write("\nНарушения ограничений, режим %s:\n" % summary["mode"])
    if not violations:
        sys.stdout.write("  нет\n")
        return
    for code, count in violations.items():
        sys.stdout.write("  %-24s %d\n" % (code, count))


def print_risk_markers(summary: Dict[str, Any]) -> None:
    markers = summary.get("risk_markers") or {}
    sys.stdout.write(
        "\nПризнаки риска в тексте, режим %s: кейсов с признаком %d из %d\n"
        % (summary["mode"], summary.get("risk_cases", 0), summary["total"])
    )
    if not markers:
        sys.stdout.write("  ни один шаблон не сработал\n")
        return
    for label, count in markers.items():
        sys.stdout.write(
            "  %-14s %-34s %d\n" % (label, spec7.RISK_LABEL_TITLES.get(label, ""), count)
        )


def print_groups(summary: Dict[str, Any]) -> None:
    groups = summary.get("groups") or {}
    sys.stdout.write("\nПо группам, режим %s:\n" % summary["mode"])
    sys.stdout.write(
        "  %-12s %-7s %-10s %-10s %-10s %-8s\n"
        % ("группа", "кейсов", "accuracy", "missed_em", "false_em", "FAIL")
    )
    for name in spec7.GROUPS:
        bucket = groups.get(name)
        if bucket is None:
            continue
        sys.stdout.write(
            "  %-12s %-7d %-10.4f %-10d %-10d %-8d\n"
            % (
                name,
                bucket["total"],
                bucket["accuracy"],
                bucket["missed_emergency"],
                bucket["false_emergency"],
                bucket["rejected"],
            )
        )
    for name in sorted(groups):
        if name in spec7.GROUPS:
            continue
        bucket = groups[name]
        sys.stdout.write(
            "  %-12s %-7d %-10.4f %-10d %-10d %-8d\n"
            % (
                name,
                bucket["total"],
                bucket["accuracy"],
                bucket["missed_emergency"],
                bucket["false_emergency"],
                bucket["rejected"],
            )
        )


def print_confusion(summary: Dict[str, Any]) -> None:
    matrix = summary.get("confusion") or {}
    sys.stdout.write("\nМатрица ошибок (строка - золотой маршрут), режим %s:\n" % summary["mode"])
    columns = list(spec7.ROUTES) + [NO_ROUTE]
    sys.stdout.write("  %-14s" % "gold \\ pred")
    for column in columns:
        sys.stdout.write("%-14s" % column)
    sys.stdout.write("\n")
    for gold in spec7.ROUTES:
        row = matrix.get(gold)
        if row is None:
            continue
        sys.stdout.write("  %-14s" % gold)
        for column in columns:
            sys.stdout.write("%-14d" % row.get(column, 0))
        sys.stdout.write("\n")


def write_report(path: str, report: Dict[str, Any]) -> None:
    out_dir = os.path.dirname(path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cases = load_cases(args.cases_path)
    except ReportInputError as cases_error:
        sys.stderr.write("Не могу прочитать кейсы: %s\n" % cases_error)
        return EXIT_DATA_ERROR

    summaries: Dict[str, Dict[str, Any]] = {}
    problems: List[str] = []
    for mode, path in (
        (spec7.MODE_BASELINE, args.baseline_path),
        (spec7.MODE_PIPELINE, args.pipeline_path),
    ):
        try:
            summaries[mode] = summarize(read_jsonl(path), cases, mode)
        except ReportInputError as read_error:
            problems.append("%s: %s" % (mode, read_error))

    if not summaries:
        sys.stderr.write("Нет ни одного прогона для сводки:\n  %s\n" % "\n  ".join(problems))
        return EXIT_DATA_ERROR

    for problem in problems:
        sys.stdout.write("ВНИМАНИЕ: прогон не прочитан - %s\n" % problem)

    print_comparison(summaries)
    for mode in (spec7.MODE_BASELINE, spec7.MODE_PIPELINE):
        summary = summaries.get(mode)
        if summary is None:
            continue
        print_groups(summary)
        print_violations(summary)
        print_risk_markers(summary)
        print_confusion(summary)

    report = {
        "cases_path": args.cases_path,
        "cases_total": len(cases),
        "inference_location": dominant_location(
            {
                summary["inference_location"]: summary["total"]
                for summary in summaries.values()
            }
        ),
        "price": price_block(summaries),
        "thresholds": {
            "ok": spec7.OK_THRESHOLD,
            "unsure": spec7.UNSURE_THRESHOLD,
            "weights": {
                "vote": spec7.W_VOTE,
                "self_check": spec7.W_SELF_CHECK,
                "self_report": spec7.W_SELF_REPORT,
            },
        },
        "modes": summaries,
        "problems": problems,
    }
    write_report(args.out_path, report)
    sys.stdout.write("\nОтчёт записан в %s\n" % args.out_path)

    controlled = summaries.get(spec7.MODE_PIPELINE)
    if controlled is None:
        sys.stdout.write("Прогон pipeline отсутствует, блокирующая метрика не проверена.\n")
        return EXIT_OK
    if controlled["missed_emergency"] > 0:
        sys.stdout.write(
            "БЛОКИРУЮЩАЯ МЕТРИКА: pipeline пропустил экстренных случаев: %d. Целевое значение - ноль.\n"
            % controlled["missed_emergency"]
        )
        return EXIT_BLOCKED
    sys.stdout.write("Блокирующая метрика в норме: pipeline не пропустил ни одного EMERGENCY.\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
