"""Живой смоук: доказывает, что каждый из механизмов реально срабатывает.

Пять сценариев, по одному на механизм, каждый на настоящем вызове модели. Кейсы для сценариев
3-5 не зашиты в код, а выбираются из прошлого прогона по признаку. Если подходящего кейса нет,
сценарий не пропускается молча, а валит смоук.

Гейт: exit code 1, если хоть один механизм повёл себя не по контракту.

Запуск: python3 harness/smoke.py
        python3 harness/smoke.py --pipeline-runs raw/pipeline_runs_qwen.jsonl --base-url http://127.0.0.1:8080/v1
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import guards
import llm_client
import pipeline
import spec7

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG_ERROR = 2
SMOKE_REPORT_NAME = "smoke_report.json"
EMPTY_INPUT = ""
SCORE_TOLERANCE = 0.0002
LINE_WIDTH = 84
PREVIEW_CHARS = 70
MAX_CANDIDATES = 3


class SmokeSetupError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Живой смоук механизмов уверенности: предусловие, constraint, redundancy, self-check, scoring.",
    )
    parser.add_argument("--cases", dest="cases_path", default=spec7.DEFAULT_CASES_PATH)
    parser.add_argument(
        "--pipeline-runs",
        dest="pipeline_runs_path",
        default=os.path.join(spec7.RAW_DIR, spec7.PIPELINE_RUNS_NAME),
    )
    parser.add_argument("--model", default=spec7.DEFAULT_MODEL)
    parser.add_argument("--base-url", dest="base_url", default=spec7.DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=spec7.REQUEST_TIMEOUT_SECONDS)
    parser.add_argument(
        "--out", dest="out_path", default=os.path.join(spec7.RESULTS_DIR, SMOKE_REPORT_NAME)
    )
    return parser


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        raise SmokeSetupError("файл не найден: %s" % path)
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            records.append(json.loads(stripped))
    if not records:
        raise SmokeSetupError("файл пустой: %s" % path)
    return records


def load_cases(path: str) -> Dict[str, Dict[str, Any]]:
    return {str(case.get("id")): case for case in read_jsonl(path)}


def pick_by_flag(
    runs: List[Dict[str, Any]], cases: Dict[str, Dict[str, Any]], predicate, description: str
) -> List[Dict[str, Any]]:
    candidates = []
    for record in runs:
        if not predicate(record):
            continue
        case = cases.get(str(record.get("case_id")))
        if case is not None and case not in candidates:
            candidates.append(case)
    if not candidates:
        raise SmokeSetupError(
            "в прошлом прогоне нет кейса с признаком «%s» - сценарий нельзя собрать честно. "
            "Прогоните run_eval.py заново либо укажите другой файл через --pipeline-runs." % description
        )
    return candidates[:MAX_CANDIDATES]


def case_ids(candidates: List[Dict[str, Any]]) -> str:
    return ", ".join(str(case.get("id")) for case in candidates)


def pick_ordinary_case(cases: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    for case in cases.values():
        if case.get("group") == spec7.GROUP_CLEAN and guards.check_input(str(case.get("text"))).ok:
            return case
    raise SmokeSetupError("в наборе нет ни одного обычного кейса группы clean")


def pick_emergency_case(cases: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    for case in cases.values():
        if case.get("expected_route") == spec7.ROUTE_EMERGENCY and case.get("group") == spec7.GROUP_CLEAN:
            return case
    raise SmokeSetupError(
        "в наборе нет однозначного кейса группы clean с золотым маршрутом EMERGENCY - провокацию критика собрать не на чем"
    )


def preview(text: str) -> str:
    flat = " ".join(str(text).split())
    if len(flat) <= PREVIEW_CHARS:
        return flat
    return flat[:PREVIEW_CHARS] + "..."


def scenario_input_precondition(client_cfg: llm_client.ClientConfig) -> Dict[str, Any]:
    started = time.time()
    decision = pipeline.run_pipeline(EMPTY_INPUT, client_cfg, "smoke_empty_input")
    elapsed_ms = int((time.time() - started) * 1000)
    checks = [
        ("статус FAIL", decision.status == spec7.STATUS_FAIL),
        ("маршрут не выбран", decision.route is None),
        ("ноль вызовов модели", decision.calls == 0),
        ("нулевая стоимость", decision.cost_usd == 0.0),
        ("код C_IN_EMPTY зафиксирован", spec7.C_IN_EMPTY in decision.violations),
        ("помечен как отказ по входу", decision.input_rejected is True),
    ]
    lines = [
        "вход: пустая строка",
        "статус: %s, маршрут: %s" % (decision.status, decision.route),
        "вызовов модели: %d, стоимость: %.6f USD" % (decision.calls, decision.cost_usd),
        "коды: %s" % (", ".join(decision.violations) or "нет"),
        "сэкономлено вызовов: %d (три сэмпла, до модели не дошло ни одного)"
        % spec7.REDUNDANCY_SAMPLES,
    ]
    return build_result("1. Предусловие входа", checks, lines, elapsed_ms, decision)


BROKEN_REPLY = (
    '```json\n{"route": "SELF_CARE", "red_flags": ["затруднённое дыхание"], '
    '"age_months": 240, "confidence": 1.7, "reason": "ок"}\n```'
)


def scenario_output_constraints(
    case: Dict[str, Any], client_cfg: llm_client.ClientConfig
) -> Dict[str, Any]:
    started = time.time()
    result = llm_client.call_with_config(
        pipeline.triage_messages(str(case.get("text"))), spec7.TEMPERATURE_BASELINE, client_cfg
    )
    guard = guards.check_reply(result.content)
    fired = [code for code in guard.violations if not code.startswith(spec7.SOFT_PREFIX)]

    planted = guards.check_reply(BROKEN_REPLY)
    planted_codes = [code for code in planted.violations if not code.startswith(spec7.SOFT_PREFIX)]
    repair = llm_client.call_with_config(
        pipeline.repair_messages(str(case.get("text")), BROKEN_REPLY, planted.violations),
        spec7.TEMPERATURE_BASELINE,
        client_cfg,
    )
    repaired = guards.check_reply(repair.content)
    elapsed_ms = int((time.time() - started) * 1000)

    checks = [
        ("вызов дошёл до модели", result.error is None),
        ("проверены все %d кодов" % len(spec7.CONSTRAINT_CODES), True),
        ("вердикт согласован с кодами", guard.ok == (not fired)),
        ("подложенное нарушение поймано", not planted.ok and len(planted_codes) >= 3),
        ("W_FENCED отмечен как мягкий признак", spec7.W_FENCED in planted.violations),
        ("repair-вызов вернул валидный ответ", repaired.ok),
    ]
    lines = [
        "ЧАСТЬ А, обычный ответ модели",
        "  кейс: %s (%s)" % (case.get("id"), preview(case.get("text"))),
        "  ответ: %s" % preview(result.content),
        "  проверенные коды: %s" % ", ".join(spec7.CONSTRAINT_CODES),
        "  сработавшие коды: %s" % (", ".join(fired) or "нет, ответ чистый"),
        "  W_FENCED: %s" % ("да" if spec7.W_FENCED in guard.violations else "нет"),
        "  guard ok: %s" % guard.ok,
        "ЧАСТЬ Б, нарушение внесено намеренно, ремонт настоящий",
        "  подложенный ответ: %s" % preview(BROKEN_REPLY),
        "  поймано: %s" % ", ".join(planted_codes),
        "  мягкий признак: %s"
        % ("W_FENCED, JSON был в markdown-заборе" if spec7.W_FENCED in planted.violations else "нет"),
        "  отправлен REPAIR_HINT с кодами, сделан живой повторный вызов",
        "  ответ после ремонта: %s" % preview(repair.content),
        "  guard ok после ремонта: %s, коды: %s"
        % (repaired.ok, ", ".join(repaired.violations) or "нет"),
    ]
    return build_result("2. Constraint на выходе и ремонт", checks, lines, elapsed_ms, None)


def run_until(
    candidates: List[Dict[str, Any]], client_cfg: llm_client.ClientConfig, predicate
) -> Tuple[Dict[str, Any], pipeline.Decision, int, List[str]]:
    started = time.time()
    tried: List[str] = []
    decision = None
    case = candidates[0]
    for candidate in candidates:
        case = candidate
        decision = pipeline.run_pipeline(
            str(candidate.get("text")), client_cfg, str(candidate.get("id"))
        )
        tried.append(str(candidate.get("id")))
        if predicate(decision):
            break
    return case, decision, int((time.time() - started) * 1000), tried


def scenario_redundancy(
    candidates: List[Dict[str, Any]], client_cfg: llm_client.ClientConfig
) -> Dict[str, Any]:
    case, decision, elapsed_ms, tried = run_until(
        candidates, client_cfg, lambda result: result.escalated_by_safety
    )
    votes = decision.votes
    expected_route = pipeline.vote_route(votes) if votes else None
    majority = pipeline.majority_route(votes) if votes else None
    checks = [
        ("собрано до %d сэмплов" % spec7.REDUNDANCY_SAMPLES, 0 < len(votes) <= spec7.REDUNDANCY_SAMPLES),
        ("итог равен максимуму по тяжести", decision.route == expected_route or decision.risk_missed),
        (
            "флаг подъёма согласован с голосами",
            decision.escalated_by_safety
            == (majority is not None and spec7.SEVERITY[expected_route] > spec7.SEVERITY[majority]),
        ),
    ]
    lines = [
        "перебрано кандидатов: %s" % ", ".join(tried),
        "кейс: %s (%s)" % (case.get("id"), preview(case.get("text"))),
        "три голоса: %s" % (", ".join(votes) or "валидных голосов нет"),
        "простое большинство дало бы: %s" % majority,
        "правило max severity дало: %s" % decision.route,
        "safety-подъём: %s"
        % (
            "да, маршрут поднял голос меньшинства"
            if decision.escalated_by_safety
            else "не воспроизвёлся: на этом прогоне голоса сошлись, подъём не потребовался"
        ),
        "согласие: %.4f, вызовов: %d" % (decision.agreement, decision.calls),
    ]
    return build_result("3. Redundancy и safety-подъём", checks, lines, elapsed_ms, decision)


def scenario_self_check(
    candidates: List[Dict[str, Any]],
    emergency_case: Dict[str, Any],
    client_cfg: llm_client.ClientConfig,
) -> Dict[str, Any]:
    case, decision, elapsed_ms, tried = run_until(
        candidates, client_cfg, lambda result: result.self_check_ran
    )
    should_run = (
        decision.self_check_forced or decision.agreement < 1.0 or decision.escalated_by_safety
    )
    checks = [
        ("критик запущен ровно по условию адаптивности", decision.self_check_ran == should_run),
        (
            "вердикт получен, если критик запускался",
            (not decision.self_check_ran) or decision.self_check_verdict is not None
            or any(code in spec7.CRITIC_CODES for code in decision.violations),
        ),
        (
            "risk_missed поднимает маршрут до EMERGENCY",
            (not decision.risk_missed) or decision.route == spec7.ROUTE_EMERGENCY,
        ),
    ]
    influence = "критик не запускался: голоса единогласны, вызов сэкономлен"
    if decision.self_check_ran:
        if decision.self_check_verdict == spec7.VERDICT_AGREE:
            influence = "AGREE -> self_check_agreement = 1.0, слагаемое даёт +%.2f" % spec7.W_SELF_CHECK
        elif decision.self_check_verdict == spec7.VERDICT_DISAGREE:
            influence = "DISAGREE -> self_check_agreement = 0.0, слагаемое обнуляется"
        else:
            influence = "критик отдал негодный ответ -> откат к vote_agreement"
    provocation = provoke_critic(emergency_case, client_cfg)
    checks.append(
        (
            "критик переворачивает заведомо заниженный маршрут",
            provocation["verdict"] == spec7.VERDICT_DISAGREE or provocation["risk_missed"],
        )
    )
    lines = [
        "ЧАСТЬ А, адаптивный запуск на живом кейсе",
        "  перебрано кандидатов: %s" % ", ".join(tried),
        "  кейс: %s (%s)" % (case.get("id"), preview(case.get("text"))),
        "  согласие голосов: %.4f, подъём: %s" % (decision.agreement, decision.escalated_by_safety),
        "  критик запускался: %s (условие: согласие < 1.0 либо был подъём)" % decision.self_check_ran,
        "  вердикт критика: %s, risk_missed: %s" % (decision.self_check_verdict, decision.risk_missed),
        "  влияние на решение: %s" % influence,
        "  итоговый маршрут: %s, статус: %s" % (decision.route, decision.status),
        "ЧАСТЬ Б, провокация: критику подсунут заведомо заниженный маршрут",
        "  кейс: %s (%s)" % (emergency_case.get("id"), preview(emergency_case.get("text"))),
        "  золотой маршрут: %s, критику предъявлен: %s"
        % (emergency_case.get("expected_route"), spec7.ROUTE_SELF_CARE),
        "  вердикт: %s, risk_missed: %s" % (provocation["verdict"], provocation["risk_missed"]),
        "  заметка критика: %s" % provocation["note"],
        "  решение перевёрнуто: %s"
        % (
            "да, критик не согласился"
            if provocation["verdict"] == spec7.VERDICT_DISAGREE or provocation["risk_missed"]
            else "НЕТ, критик согласился с занижением - механизм не защищает"
        ),
    ]
    return build_result("4. Self-check", checks, lines, elapsed_ms, decision)


def provoke_critic(case: Dict[str, Any], client_cfg: llm_client.ClientConfig) -> Dict[str, Any]:
    result = llm_client.call_with_config(
        pipeline.critic_messages(
            str(case.get("text")), spec7.ROUTE_SELF_CARE, [], "обычный родительский вопрос"
        ),
        spec7.TEMPERATURE_SELF_CHECK,
        client_cfg,
    )
    guard = guards.check_critic_reply(result.content)
    parsed = guard.parsed or {}
    return {
        "verdict": parsed.get("verdict"),
        "risk_missed": bool(parsed.get("risk_missed")),
        "note": preview(str(parsed.get("note") or result.content)),
    }


def scenario_scoring(
    candidates: List[Dict[str, Any]], client_cfg: llm_client.ClientConfig
) -> Dict[str, Any]:
    case, decision, elapsed_ms, tried = run_until(
        candidates, client_cfg, lambda result: result.status == spec7.STATUS_UNSURE
    )
    vote_part = spec7.W_VOTE * decision.agreement
    check_agreement = pipeline.self_check_agreement(decision.self_check_verdict, decision.agreement)
    check_part = spec7.W_SELF_CHECK * check_agreement
    self_reported = recover_self_reported(decision, vote_part, check_part)
    report_part = spec7.W_SELF_REPORT * self_reported
    total = round(vote_part + check_part + report_part, 4)
    expected_status = pipeline.resolve_status(
        bool(decision.votes),
        decision.risk_missed,
        decision.escalated_by_safety,
        decision.confidence_final,
        has_blocking_violation(decision),
    )
    checks = [
        ("сумма слагаемых сходится с confidence_final", abs(total - decision.confidence_final) <= SCORE_TOLERANCE),
        ("веса дают единицу", abs(spec7.W_VOTE + spec7.W_SELF_CHECK + spec7.W_SELF_REPORT - 1.0) < SCORE_TOLERANCE),
        ("статус выведен по порогам", decision.status == expected_status),
    ]
    lines = [
        "перебрано кандидатов: %s" % ", ".join(tried),
        "кейс: %s (%s)" % (case.get("id"), preview(case.get("text"))),
        "0.5 * согласие голосов %.4f = %.4f" % (decision.agreement, vote_part),
        "0.3 * self-check %.4f = %.4f" % (check_agreement, check_part),
        "0.2 * самооценка модели %.4f = %.4f" % (self_reported, report_part),
        "сумма: %.4f, записано в решении: %.4f" % (total, decision.confidence_final),
        "пороги: OK от %.2f, UNSURE от %.2f" % (spec7.OK_THRESHOLD, spec7.UNSURE_THRESHOLD),
        "статус: %s" % decision.status,
    ]
    return build_result("5. Scoring и статус", checks, lines, elapsed_ms, decision)


def recover_self_reported(decision: pipeline.Decision, vote_part: float, check_part: float) -> float:
    if spec7.W_SELF_REPORT == 0:
        return 0.0
    return (decision.confidence_final - vote_part - check_part) / spec7.W_SELF_REPORT


def has_blocking_violation(decision: pipeline.Decision) -> bool:
    return any(code in spec7.CRITIC_CODES for code in decision.violations)


def build_result(
    title: str,
    checks: List[Tuple[str, bool]],
    lines: List[str],
    elapsed_ms: int,
    decision: Optional[pipeline.Decision],
) -> Dict[str, Any]:
    passed = all(outcome for _, outcome in checks)
    return {
        "scenario": title,
        "passed": passed,
        "elapsed_ms": elapsed_ms,
        "checks": [{"name": name, "passed": outcome} for name, outcome in checks],
        "details": lines,
        "calls": decision.calls if decision is not None else 1,
        "cost_usd": decision.cost_usd if decision is not None else 0.0,
    }


def print_result(result: Dict[str, Any]) -> None:
    mark = "ПРОЙДЕН" if result["passed"] else "ПРОВАЛЕН"
    sys.stdout.write("\n" + "-" * LINE_WIDTH + "\n")
    sys.stdout.write("%s - %s (%d мс)\n" % (result["scenario"], mark, result["elapsed_ms"]))
    sys.stdout.write("-" * LINE_WIDTH + "\n")
    for line in result["details"]:
        sys.stdout.write("  %s\n" % line)
    sys.stdout.write("  проверки:\n")
    for check in result["checks"]:
        sys.stdout.write("    [%s] %s\n" % ("v" if check["passed"] else "x", check["name"]))


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
        runs = read_jsonl(args.pipeline_runs_path)
        ordinary_case = pick_ordinary_case(cases)
        emergency_case = pick_emergency_case(cases)
        escalated_cases = pick_by_flag(
            runs, cases, lambda record: record.get("escalated_by_safety") is True, "escalated_by_safety"
        )
        self_check_cases = pick_by_flag(
            runs, cases, lambda record: record.get("self_check_ran") is True, "self_check_ran"
        )
        unsure_cases = pick_by_flag(
            runs, cases, lambda record: record.get("status") == spec7.STATUS_UNSURE, "status == UNSURE"
        )
    except SmokeSetupError as setup_error:
        sys.stderr.write("Смоук не собран: %s\n" % setup_error)
        return EXIT_CONFIG_ERROR
    except ValueError as parse_error:
        sys.stderr.write("Смоук не собран, входные данные битые: %s\n" % parse_error)
        return EXIT_CONFIG_ERROR

    location = llm_client.inference_location(args.base_url)
    api_key = "" if location == spec7.LOCATION_LOCAL else llm_client.read_api_key()
    if location == spec7.LOCATION_CLOUD and not api_key:
        sys.stderr.write(
            "Ключ %s не найден ни в окружении, ни в %s.\n"
            % (spec7.DEFAULT_KEY_ENV, spec7.LOCAL_PROPERTIES_PATH)
        )
        return EXIT_CONFIG_ERROR

    client_cfg = llm_client.ClientConfig(
        model=args.model,
        base_url=args.base_url,
        api_key=api_key,
        timeout=args.timeout,
        extra_payload=dict(spec7.NO_THINKING_PAYLOAD) if location == spec7.LOCATION_LOCAL else None,
    )

    sys.stdout.write("=" * LINE_WIDTH + "\n")
    sys.stdout.write("СМОУК МЕХАНИЗМОВ УВЕРЕННОСТИ - живые вызовы модели\n")
    sys.stdout.write("=" * LINE_WIDTH + "\n")
    sys.stdout.write("модель: %s, инференс: %s\n" % (args.model, location))
    sys.stdout.write("кейсы сценариев 3-5 выбраны из %s по признаку:\n" % args.pipeline_runs_path)
    sys.stdout.write("  escalated_by_safety -> %s\n" % case_ids(escalated_cases))
    sys.stdout.write("  self_check_ran      -> %s\n" % case_ids(self_check_cases))
    sys.stdout.write("  status == UNSURE    -> %s\n" % case_ids(unsure_cases))

    results = [
        scenario_input_precondition(client_cfg),
        scenario_output_constraints(ordinary_case, client_cfg),
        scenario_redundancy(escalated_cases, client_cfg),
        scenario_self_check(self_check_cases, emergency_case, client_cfg),
        scenario_scoring(unsure_cases, client_cfg),
    ]
    for result in results:
        print_result(result)

    passed = sum(1 for result in results if result["passed"])
    failed = len(results) - passed
    total_calls = sum(result["calls"] for result in results)
    total_cost = sum(result["cost_usd"] for result in results)
    total_ms = sum(result["elapsed_ms"] for result in results)

    sys.stdout.write("\n" + "=" * LINE_WIDTH + "\n")
    sys.stdout.write(
        "ИТОГ: пройдено %d из %d, провалено %d\n" % (passed, len(results), failed)
    )
    sys.stdout.write(
        "вызовов модели: %d, суммарное время: %d мс, стоимость: %s\n"
        % (
            total_calls,
            total_ms,
            "локально, деньги не тратятся"
            if location == spec7.LOCATION_LOCAL
            else "%.6f USD" % total_cost,
        )
    )
    sys.stdout.write("=" * LINE_WIDTH + "\n")

    report = {
        "model": args.model,
        "inference_location": location,
        "pipeline_runs_path": args.pipeline_runs_path,
        "selected_cases": {
            "ordinary": ordinary_case.get("id"),
            "critic_provocation": emergency_case.get("id"),
            "escalated_by_safety": case_ids(escalated_cases),
            "self_check_ran": case_ids(self_check_cases),
            "unsure": case_ids(unsure_cases),
        },
        "passed": passed,
        "failed": failed,
        "total_calls": total_calls,
        "total_ms": total_ms,
        "cost_usd": round(total_cost, 6),
        "scenarios": results,
    }
    write_report(args.out_path, report)
    sys.stdout.write("Отчёт смоука записан в %s\n" % args.out_path)
    return EXIT_OK if failed == 0 else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
