"""Прогон набора кейсов через input_guard/output_guard без единого сетевого вызова.

Ревизия 2026-08-05 (контракт раздел 15): числа с dev-набора (data/cases.jsonl.b64) не считаются
результатом защиты - его писал тот же, кто писал детекторы. Главная цифра отчёта - прогон по
data/holdout_cases.jsonl.b64, слепому набору от другого исполнителя. Схема кейса определяется по
составу полей, не по имени файла: expect_verdict + expect_reasons - dev, expect_caught + what +
family - holdout. Гейт целостности замера (exit 1 при провале) действует только для dev - плохой
результат на holdout это факт отчёта, а не повод ронять сборку.

Наборы в data/ хранятся закодированными построчным base64 (расширение .jsonl.b64) - см. README
раздел про наборы кейсов и harness/case_codec.py. read_jsonl декодирует прозрачно, дальше всё как
было. Посмотреть набор глазами - harness/show_cases.py.

Запуск: python3 harness/run_tests.py                                       # dev
        python3 harness/run_tests.py --verbose
        python3 harness/run_tests.py --dry-run
        python3 harness/run_tests.py --cases data/holdout_cases.jsonl.b64   # -> results/holdout_tests.json
        python3 harness/run_tests.py --cases data/holdout2_cases.jsonl.b64  # -> results/holdout2_tests.json

Путь отчёта для holdout выводится из имени файла кейсов (holdout_cases.jsonl.b64 -> holdout_tests.json,
holdout2_cases.jsonl.b64 -> holdout2_tests.json), поэтому второй и третий слепые наборы не затирают
первый - см. default_holdout_out_path. --out переопределяет путь явно, если нужно другое имя.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Set

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import case_codec
import input_guard
import output_guard
import spec13

BUCKET_CAUGHT = "caught"
BUCKET_MISSED = "missed"
BUCKET_FALSE_POSITIVE = "false_positive"
BUCKET_WRONG_REASONS = "caught_wrong_reasons"
BUCKET_CORRECT_CLEAN = "correct_clean"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Прогон тест-набора guard-детекторов task13")
    parser.add_argument("--cases", dest="cases_path", default=spec13.CASES_PATH)
    parser.add_argument("--out", dest="out_path", default=None)
    parser.add_argument("--verbose", dest="verbose", action="store_true")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    return parser


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in case_codec.read_case_lines(path)]


def case_messages(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "messages" in case:
        return case["messages"]
    return [{"role": "user", "content": case.get("text", "")}]


def case_schema(case: Dict[str, Any]) -> str:
    if "expect_caught" in case:
        return spec13.CASE_SCHEMA_HOLDOUT
    if "expect_verdict" in case:
        return spec13.CASE_SCHEMA_DEV
    raise ValueError("кейс %r не содержит ни expect_verdict, ни expect_caught" % case.get("id"))


def detect_run_schema(cases: List[Dict[str, Any]]) -> str:
    if not cases:
        raise ValueError("набор кейсов пуст")
    schemas: Set[str] = {case_schema(case) for case in cases}
    if len(schemas) > 1:
        raise ValueError("набор кейсов смешивает схемы dev и holdout в одном файле: %s" % sorted(schemas))
    return schemas.pop()


def case_file_stem(cases_path: str) -> str:
    basename = os.path.basename(cases_path)
    for suffix in (".jsonl" + case_codec.ENCODED_SUFFIX, ".jsonl"):
        if basename.endswith(suffix):
            return basename[: -len(suffix)]
    return os.path.splitext(basename)[0]


def default_holdout_out_path(cases_path: str) -> str:
    stem = case_file_stem(cases_path)
    if stem.endswith("_cases"):
        stem = stem[: -len("_cases")] + "_tests"
    else:
        stem = stem + "_tests"
    return os.path.join(spec13.RESULTS_DIR, stem + ".json")


def run_guard(case: Dict[str, Any]) -> Any:
    kind = case["kind"]
    if kind == spec13.CASE_KIND_INPUT:
        return input_guard.check_input(case_messages(case))
    if kind == spec13.CASE_KIND_OUTPUT:
        return output_guard.check_output(case.get("text", ""), case.get("input_text", ""))
    raise ValueError("неизвестный kind у кейса %r: %r" % (case.get("id"), kind))


def run_case_dev(case: Dict[str, Any]) -> Dict[str, Any]:
    expect_verdict = case["expect_verdict"]
    expect_reasons = set(case.get("expect_reasons", []))
    result = run_guard(case)
    actual_verdict = result.verdict
    actual_reasons = set(result.reasons)

    if expect_verdict == spec13.VERDICT_PASS:
        bucket = BUCKET_CAUGHT if actual_verdict == spec13.VERDICT_PASS else BUCKET_FALSE_POSITIVE
    elif actual_verdict == spec13.VERDICT_PASS:
        bucket = BUCKET_MISSED
    elif actual_verdict == expect_verdict and actual_reasons == expect_reasons:
        bucket = BUCKET_CAUGHT
    else:
        bucket = BUCKET_WRONG_REASONS

    return {
        "id": case.get("id"),
        "kind": case["kind"],
        "note": case.get("note", ""),
        "expect_verdict": expect_verdict,
        "expect_reasons": sorted(expect_reasons),
        "actual_verdict": actual_verdict,
        "actual_reasons": sorted(actual_reasons),
        "bucket": bucket,
    }


def run_case_holdout(case: Dict[str, Any]) -> Dict[str, Any]:
    expect_caught = bool(case["expect_caught"])
    result = run_guard(case)
    actual_verdict = result.verdict
    actual_reasons = sorted(result.reasons)
    actual_caught = actual_verdict != spec13.VERDICT_PASS

    if expect_caught and actual_caught:
        bucket = BUCKET_CAUGHT
    elif expect_caught and not actual_caught:
        bucket = BUCKET_MISSED
    elif not expect_caught and actual_caught:
        bucket = BUCKET_FALSE_POSITIVE
    else:
        bucket = BUCKET_CORRECT_CLEAN

    return {
        "id": case.get("id"),
        "kind": case["kind"],
        "family": case.get("family", ""),
        "what": case.get("what", ""),
        "expect_caught": expect_caught,
        "actual_caught": actual_caught,
        "actual_verdict": actual_verdict,
        "actual_reasons": actual_reasons,
        "bucket": bucket,
    }


def evaluate_gates_dev(cases: List[Dict[str, Any]], records: List[Dict[str, Any]]) -> Dict[str, bool]:
    self_trigger_ids = {case["id"] for case in cases if "self" in case["id"]}
    self_trigger_ok = all(
        record["bucket"] == BUCKET_CAUGHT
        for record in records
        if record["id"] in self_trigger_ids and record["expect_verdict"] == spec13.VERDICT_PASS
    )
    return {
        spec13.GATE_MIN_CASES: len(cases) >= spec13.MIN_CASE_COUNT,
        spec13.GATE_NO_FALSE_POSITIVE: not any(record["bucket"] == BUCKET_FALSE_POSITIVE for record in records),
        spec13.GATE_NO_SELF_TRIGGER: self_trigger_ok,
        spec13.GATE_VERDICT_MATCH: all(record["bucket"] == BUCKET_CAUGHT for record in records),
    }


def print_dry_run(cases: List[Dict[str, Any]], schema: str) -> None:
    by_kind: Dict[str, int] = {}
    for case in cases:
        by_kind[case.get("kind", "?")] = by_kind.get(case.get("kind", "?"), 0) + 1
    sys.stdout.write("Схема кейсов: %s\n" % schema)
    sys.stdout.write("Прогон без единого запроса к API - все проверки локальные.\n")
    sys.stdout.write("Кейсов всего: %d, вызовов сети: 0, оценка стоимости: 0.000000 USD\n" % len(cases))
    sys.stdout.write("По типу: %s\n" % json.dumps(by_kind, ensure_ascii=False))

    if schema == spec13.CASE_SCHEMA_DEV:
        by_verdict: Dict[str, int] = {}
        for case in cases:
            by_verdict[case.get("expect_verdict", "?")] = by_verdict.get(case.get("expect_verdict", "?"), 0) + 1
        sys.stdout.write("По ожидаемому вердикту: %s\n" % json.dumps(by_verdict, ensure_ascii=False))
        return

    by_expect_caught: Dict[str, int] = {}
    by_family: Dict[str, int] = {}
    for case in cases:
        key = "true" if case.get("expect_caught") else "false"
        by_expect_caught[key] = by_expect_caught.get(key, 0) + 1
        family = case.get("family", "?")
        by_family[family] = by_family.get(family, 0) + 1
    sys.stdout.write("По expect_caught: %s\n" % json.dumps(by_expect_caught, ensure_ascii=False))
    sys.stdout.write("По family: %s\n" % json.dumps(by_family, ensure_ascii=False))


def print_table_dev(records: List[Dict[str, Any]]) -> None:
    counts = {BUCKET_CAUGHT: 0, BUCKET_MISSED: 0, BUCKET_FALSE_POSITIVE: 0, BUCKET_WRONG_REASONS: 0}
    for record in records:
        counts[record["bucket"]] += 1
    sys.stdout.write("\n[dev, data/cases.jsonl.b64 - писался со знанием реализации, не итоговая цифра]\n")
    sys.stdout.write("Всего кейсов: %d\n" % len(records))
    sys.stdout.write("%-24s %d\n" % ("поймано", counts[BUCKET_CAUGHT]))
    sys.stdout.write("%-24s %d\n" % ("пропущено", counts[BUCKET_MISSED]))
    sys.stdout.write("%-24s %d\n" % ("ложное срабатывание", counts[BUCKET_FALSE_POSITIVE]))
    sys.stdout.write("%-24s %d\n" % ("верно, но причина иная", counts[BUCKET_WRONG_REASONS]))


def print_verbose_dev(records: List[Dict[str, Any]]) -> None:
    sys.stdout.write("\nПо кейсам:\n")
    for record in records:
        mark = "OK" if record["bucket"] == BUCKET_CAUGHT else record["bucket"].upper()
        sys.stdout.write(
            "  [%-24s] %-6s ожид=%s%s факт=%s%s\n"
            % (
                record["id"], mark, record["expect_verdict"], record["expect_reasons"],
                record["actual_verdict"], record["actual_reasons"],
            )
        )


def print_misses_dev(records: List[Dict[str, Any]]) -> None:
    problems = [record for record in records if record["bucket"] != BUCKET_CAUGHT]
    if not problems:
        return
    sys.stdout.write("\nКейсы, которые не поймались как ожидалось:\n")
    for record in problems:
        sys.stdout.write(
            "  %s (%s): ожидали %s%s, получили %s%s - %s\n"
            % (
                record["id"], record["bucket"], record["expect_verdict"], record["expect_reasons"],
                record["actual_verdict"], record["actual_reasons"], record["note"],
            )
        )


def family_breakdown(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    attack_records = [record for record in records if record["expect_caught"]]
    families = sorted({record["family"] for record in attack_records})
    breakdown = []
    for family in families:
        family_records = [record for record in attack_records if record["family"] == family]
        caught = sum(1 for record in family_records if record["bucket"] == BUCKET_CAUGHT)
        total = len(family_records)
        breakdown.append(
            {"family": family, "caught": caught, "total": total, "catch_rate": round(caught / total, 3)}
        )
    breakdown.sort(key=lambda row: (row["catch_rate"], row["family"]))
    return breakdown


def print_table_holdout(records: List[Dict[str, Any]]) -> None:
    counts = {BUCKET_CAUGHT: 0, BUCKET_MISSED: 0, BUCKET_FALSE_POSITIVE: 0, BUCKET_CORRECT_CLEAN: 0}
    for record in records:
        counts[record["bucket"]] += 1
    should_catch_total = counts[BUCKET_CAUGHT] + counts[BUCKET_MISSED]
    clean_total = counts[BUCKET_FALSE_POSITIVE] + counts[BUCKET_CORRECT_CLEAN]

    sys.stdout.write("\n[holdout, слепой набор - это главная цифра отчёта]\n")
    sys.stdout.write(
        "Всего кейсов: %d (должны были поймать: %d, чистых: %d)\n" % (len(records), should_catch_total, clean_total)
    )
    sys.stdout.write("%-24s %d из %d\n" % ("поймано", counts[BUCKET_CAUGHT], should_catch_total))
    sys.stdout.write("%-24s %d из %d\n" % ("пропущено", counts[BUCKET_MISSED], should_catch_total))
    sys.stdout.write("%-24s %d из %d\n" % ("ложное срабатывание", counts[BUCKET_FALSE_POSITIVE], clean_total))
    sys.stdout.write("%-24s %d из %d\n" % ("верно тихо (чисто)", counts[BUCKET_CORRECT_CLEAN], clean_total))

    breakdown = family_breakdown(records)
    if breakdown:
        sys.stdout.write("\nПо family (от худшей доли поимки к лучшей):\n")
        for row in breakdown:
            sys.stdout.write(
                "  %-28s %d из %d (%.0f%%)\n" % (row["family"], row["caught"], row["total"], row["catch_rate"] * 100)
            )


def print_verbose_holdout(records: List[Dict[str, Any]]) -> None:
    sys.stdout.write("\nПо кейсам:\n")
    for record in records:
        mark = record["bucket"].upper()
        sys.stdout.write(
            "  [%-24s] %-14s %-6s family=%-16s ожид_поймать=%s факт=%s\n"
            % (record["id"], mark, record["kind"], record["family"], record["expect_caught"], record["actual_verdict"])
        )


def print_misses_holdout(records: List[Dict[str, Any]]) -> None:
    problems = [record for record in records if record["bucket"] in (BUCKET_MISSED, BUCKET_FALSE_POSITIVE)]
    if not problems:
        return
    sys.stdout.write("\nКейсы holdout, где вердикт разошёлся с ожиданием:\n")
    for record in problems:
        sys.stdout.write(
            "  %s (%s, family=%s): %s - факт=%s\n"
            % (record["id"], record["bucket"], record["family"], record["what"], record["actual_verdict"])
        )


def run_dev(cases: List[Dict[str, Any]], args: argparse.Namespace) -> int:
    records = [run_case_dev(case) for case in cases]
    gates = evaluate_gates_dev(cases, records)

    print_table_dev(records)
    if args.verbose:
        print_verbose_dev(records)
    print_misses_dev(records)

    sys.stdout.write("\nГейт целостности замера (только dev, holdout порога не имеет):\n")
    gate_passed = True
    for code in spec13.GATE_CODES:
        status = gates[code]
        gate_passed = gate_passed and status
        sys.stdout.write("  [%s] %s\n" % ("OK" if status else "FAIL", spec13.GATE_TITLES[code]))

    out_path = args.out_path or spec13.GUARD_TESTS_REPORT_PATH
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    report = {
        "schema": spec13.CASE_SCHEMA_DEV,
        "cases_path": args.cases_path,
        "total_cases": len(cases),
        "counts": {
            bucket: sum(1 for record in records if record["bucket"] == bucket)
            for bucket in (BUCKET_CAUGHT, BUCKET_MISSED, BUCKET_FALSE_POSITIVE, BUCKET_WRONG_REASONS)
        },
        "gates": gates,
        "gate_passed": gate_passed,
        "records": records,
    }
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    sys.stdout.write("\nОтчёт: %s\n" % out_path)
    return spec13.EXIT_OK if gate_passed else spec13.EXIT_GATE_FAILED


def run_holdout(cases: List[Dict[str, Any]], args: argparse.Namespace) -> int:
    records = [run_case_holdout(case) for case in cases]

    print_table_holdout(records)
    if args.verbose:
        print_verbose_holdout(records)
    print_misses_holdout(records)
    sys.stdout.write("\nБез гейта: holdout-результат - факт для отчёта, не условие сборки (контракт раздел 15).\n")

    out_path = args.out_path or default_holdout_out_path(args.cases_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    report = {
        "schema": spec13.CASE_SCHEMA_HOLDOUT,
        "cases_path": args.cases_path,
        "total_cases": len(cases),
        "counts": {
            bucket: sum(1 for record in records if record["bucket"] == bucket)
            for bucket in (BUCKET_CAUGHT, BUCKET_MISSED, BUCKET_FALSE_POSITIVE, BUCKET_CORRECT_CLEAN)
        },
        "family_breakdown": family_breakdown(records),
        "records": records,
    }
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    sys.stdout.write("\nОтчёт: %s\n" % out_path)
    return spec13.EXIT_OK


def main() -> int:
    args = build_parser().parse_args()

    if not os.path.isfile(args.cases_path):
        sys.stderr.write("файл кейсов не найден: %s\n" % args.cases_path)
        return spec13.EXIT_DATA_ERROR

    cases = read_jsonl(args.cases_path)
    try:
        schema = detect_run_schema(cases)
    except ValueError as error:
        sys.stderr.write("%s\n" % error)
        return spec13.EXIT_DATA_ERROR

    if args.dry_run:
        print_dry_run(cases, schema)
        return spec13.EXIT_OK

    if schema == spec13.CASE_SCHEMA_DEV:
        return run_dev(cases, args)
    return run_holdout(cases, args)


if __name__ == "__main__":
    sys.exit(main())
