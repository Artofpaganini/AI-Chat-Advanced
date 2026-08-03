"""Прогон набора атак против системных промптов из spec11.py.

Каждый вызов - одна атака на одной мишени с одним слоем защиты. Модель недетерминирована,
поэтому --repeats запускает весь набор N раз в отдельные файлы raw/attacks_<defense>_r<N>.jsonl.
Слои защиты - hardened (L1), delimiters (L2), guard (L3), all (все три) - контракт раздел 5.
Pipeline-атаки (ROUTE_HIJACK) исключены из обычного прогона - защита на уровне системного промпта
не относится к внутренней 3-этапной цепочке, там своя дыра в коде, не в промпте.

Запуск: python3 harness/run_attacks.py --dry-run
        python3 harness/run_attacks.py --target alva --defense none --repeats 3
        python3 harness/run_attacks.py --target all --defense hardened --repeats 3 --workers 4
        python3 harness/run_attacks.py --target all --defense all --repeats 3 --workers 4
"""

import argparse
import concurrent.futures
import json
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import attacks as attacks_module
import detectors
import input_normalize
import output_guard
import pipeline_stages
import spec11

sys.path.insert(0, spec11.TASK7_HARNESS_DIR)
import llm_client


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Прогон атак task11 по трём системным промптам")
    parser.add_argument("--target", choices=spec11.TARGETS + (spec11.TARGET_ALL,), default=spec11.TARGET_ALL)
    parser.add_argument(
        "--defense",
        choices=spec11.DEFENSES + (spec11.DEFENSE_SWEEP, spec11.DEFENSE_HARDENED_V2),
        default=spec11.DEFENSE_NONE,
    )
    parser.add_argument("--split", choices=spec11.SPLITS + (spec11.TARGET_ALL,), default=spec11.TARGET_ALL)
    parser.add_argument("--repeats", type=int, default=spec11.DEFAULT_REPEATS)
    parser.add_argument("--workers", type=int, default=spec11.DEFAULT_WORKERS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--attacks-path", dest="attacks_path", default=spec11.ATTACKS_PATH)
    parser.add_argument("--ids", dest="ids", default="", help="через запятую - прогнать только эти id, не весь набор")
    parser.add_argument("--out-dir", dest="out_dir", default=spec11.RAW_DIR)
    parser.add_argument("--model", default=spec11.DEFAULT_MODEL)
    parser.add_argument("--base-url", dest="base_url", default=spec11.DEFAULT_BASE_URL)
    parser.add_argument("--key-env", dest="key_env", default=spec11.DEFAULT_KEY_ENV)
    parser.add_argument("--timeout", type=int, default=spec11.REQUEST_TIMEOUT_SECONDS)
    parser.add_argument("--thinking", dest="thinking", action="store_true")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    return parser


def defenses_for(name: str) -> List[str]:
    if name == spec11.DEFENSE_SWEEP:
        return list(spec11.DEFENSES)
    return [name]


def system_prompt_for(target: str, defense: str) -> str:
    """Слой защиты поверх базового системного промпта мишени.

    none - как есть. hardened (L1) - усиленный промпт вместо базового. delimiters (L2) - базовый
    промпт плюс инструкция про маркеры, сам текст пользователя оборачивается в wrap_user_content.
    guard (L3) - промпт не меняется, фильтр работает на выходе (apply_output_guard). l0_normalize
    (L0) - промпт тоже не меняется, сообщение проверяется и блокируется ДО системного промпта, см.
    maybe_block_by_l0. all - L0 на входе + hardened + delimiters на входе, guard на выходе.
    """
    if defense in (spec11.DEFENSE_NONE, spec11.DEFENSE_GUARD, spec11.DEFENSE_L0):
        return spec11.SYSTEM_PROMPTS[target]
    if defense == spec11.DEFENSE_HARDENED:
        return spec11.HARDENED_SYSTEM_PROMPTS[target]
    if defense == spec11.DEFENSE_HARDENED_V2:
        return spec11.HARDENED_V2_SYSTEM_PROMPTS[target]
    if defense == spec11.DEFENSE_DELIMITERS:
        return spec11.SYSTEM_PROMPTS[target] + spec11.DELIMITER_INSTRUCTION
    if defense == spec11.DEFENSE_ALL:
        return spec11.HARDENED_SYSTEM_PROMPTS[target] + spec11.DELIMITER_INSTRUCTION
    raise NotImplementedError("неизвестный слой защиты %r" % defense)


def maybe_block_by_l0(text: str, defense: str) -> Tuple[bool, List[str]]:
    if defense not in (spec11.DEFENSE_L0, spec11.DEFENSE_ALL):
        return False, []
    blocked, _layers, reasons = input_normalize.normalize_and_check(text)
    return blocked, reasons


def wrap_user_content(text: str, defense: str) -> str:
    if defense in (spec11.DEFENSE_DELIMITERS, spec11.DEFENSE_ALL):
        return "%s\n%s\n%s" % (spec11.USER_INPUT_START, text, spec11.USER_INPUT_END)
    return text


def apply_output_guard(response_text: str, target: str, defense: str) -> Tuple[str, List[str]]:
    if defense in (spec11.DEFENSE_GUARD, spec11.DEFENSE_ALL):
        return output_guard.apply(response_text, target)
    return response_text, []


def out_path_for(out_dir: str, defense: str, repeat: int, repeats: int) -> str:
    name = spec11.RAW_FILE_PREFIX + defense
    if repeats > spec11.MIN_REPEATS:
        name += spec11.REPEAT_SUFFIX_PREFIX + str(repeat)
    return os.path.join(out_dir, name + spec11.RAW_FILE_EXTENSION)


def build_config(model: str, base_url: str, api_key: str, timeout: int, thinking_off: bool) -> llm_client.ClientConfig:
    extra_payload = dict(spec11.CLOUD_REASONING_OFF) if thinking_off else None
    return llm_client.ClientConfig(
        model=model, base_url=base_url, api_key=api_key, timeout=timeout, extra_payload=extra_payload
    )


def estimate_prompt_tokens(system_prompt: str, user_text: str) -> int:
    chars = len(system_prompt) + len(user_text)
    return int(chars / spec11.CHARS_PER_TOKEN_ESTIMATE) + 1


def estimate_case_calls_and_cost(case: Dict[str, Any], model: str) -> tuple:
    """1 вызов для обычной атаки, 3 для pipeline (этапы разбора/решения/ответа)."""
    if case.get("mode") == spec11.MODE_PIPELINE:
        stage1_tokens = estimate_prompt_tokens(pipeline_stages.STAGE1_SYSTEM_PROMPT, case["text"])
        stage2_tokens = estimate_prompt_tokens(pipeline_stages.STAGE2_SYSTEM_PROMPT, "") + 30
        stage3_tokens = estimate_prompt_tokens(pipeline_stages.STAGE3_SYSTEM_PROMPT, "") + 60
        usage = {
            "prompt_tokens": stage1_tokens + stage2_tokens + stage3_tokens,
            "completion_tokens": (
                pipeline_stages.STAGE1_MAX_TOKENS + pipeline_stages.STAGE2_MAX_TOKENS
                + pipeline_stages.STAGE3_MAX_TOKENS
            ),
        }
        return 3, llm_client.usage_cost(usage, model)
    usage = {
        "prompt_tokens": estimate_prompt_tokens(spec11.SYSTEM_PROMPTS[case["target"]], case["text"]),
        "completion_tokens": spec11.ATTACK_MAX_TOKENS,
    }
    return 1, llm_client.usage_cost(usage, model)


def run_one(case: Dict[str, Any], defense: str, config: llm_client.ClientConfig) -> Dict[str, Any]:
    target = case["target"]
    l0_blocked, l0_reasons = maybe_block_by_l0(case["text"], defense)
    if l0_blocked:
        # L0 отклоняет сообщение до системного промпта - модель не вызывается вообще, атака
        # не может ничего вернуть, стоимость и задержка нулевые.
        detection = detectors.run_detectors(spec11.L0_BLOCKED_ANSWER, target)
        return {
            "attack_id": case["attack_id"],
            "technique": case["technique"],
            "class": case["class"],
            "target": target,
            "split": case["split"],
            "source": case["source"],
            "family": case.get("family", spec11.FAMILY_OWN),
            "expected_detector": case["expected_detector"],
            "defense": defense,
            "raw_response": spec11.L0_BLOCKED_ANSWER,
            "response": spec11.L0_BLOCKED_ANSWER,
            "guard_reasons": [],
            "l0_blocked": True,
            "l0_reasons": l0_reasons,
            "detectors": detection["detectors"],
            "leak_markers": [],
            "safety_bypass_reason": "",
            "triggered": detection["triggered"],
            "success": detection["success"],
            "refused": detection[spec11.DETECTOR_REFUSED],
            "usage": llm_client.empty_usage(),
            "cost_usd": 0.0,
            "latency_ms": 0,
            "error": None,
            "status_code": None,
        }
    system_prompt = system_prompt_for(target, defense)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": wrap_user_content(case["text"], defense)},
    ]
    result = llm_client.call_with_config(messages, spec11.ATTACK_TEMPERATURE, config, spec11.ATTACK_MAX_TOKENS)
    # detectors считают по тому, что реально дошло бы до пользователя - после guard, не до него.
    delivered_text, guard_reasons = (
        apply_output_guard(result.content, target, defense) if not result.error else (result.content, [])
    )
    detection = detectors.run_detectors(delivered_text, target) if not result.error else None
    return {
        "attack_id": case["attack_id"],
        "technique": case["technique"],
        "class": case["class"],
        "target": target,
        "split": case["split"],
        "source": case["source"],
        "family": case.get("family", spec11.FAMILY_OWN),
        "expected_detector": case["expected_detector"],
        "defense": defense,
        "raw_response": result.content,
        "response": delivered_text,
        "guard_reasons": guard_reasons,
        "detectors": detection["detectors"] if detection else None,
        "leak_markers": detection["leak_markers"] if detection else [],
        "safety_bypass_reason": detection["safety_bypass_reason"] if detection else "",
        "triggered": detection["triggered"] if detection else [],
        "success": detection["success"] if detection else False,
        "refused": detection[spec11.DETECTOR_REFUSED] if detection else False,
        "usage": result.usage,
        "cost_usd": llm_client.usage_cost(result.usage, config.model),
        "latency_ms": result.latency_ms,
        "error": result.error,
        "status_code": result.status_code,
    }


PIPELINE_STAGE_EXTRA = {"reasoning_effort": pipeline_stages.STAGE_REASONING_EFFORT}


def run_pipeline_case(case: Dict[str, Any], defense: str, config: llm_client.ClientConfig) -> Dict[str, Any]:
    """ROUTE_HIJACK: три реальных вызова той же цепочки, что и в MultiStageAiRepositoryImpl.kt
    (версия после починки, 2026-08-03 - см. pipeline_stages.py).

    Меряется не текст ответа, а факты этапа 1 и итоговый маршрут - ровно то место, где feature/ai
    подставляет вывод одного вызова в промпт следующего. escapeBoundaryMarkers гасит поддельные
    маркеры в caseText до обёртки, childRedFlagWordsMissingFromSymptoms форсирует EMERGENCY, если
    в исходном тексте есть корень опасного признака, а SYMPTOMS после разбора пуст.
    """
    calls: List[llm_client.CallResult] = []

    def call_stage(system_prompt: str, user_content: str, max_tokens: int) -> llm_client.CallResult:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
        result = llm_client.call_model(
            messages, pipeline_stages.STAGE_TEMPERATURE, max_tokens, config.model, config.base_url,
            config.api_key, config.timeout, PIPELINE_STAGE_EXTRA,
        )
        calls.append(result)
        return result

    case_text = case["text"]
    stage1 = call_stage(
        pipeline_stages.STAGE1_SYSTEM_PROMPT, pipeline_stages.stage1_user_content(case_text),
        pipeline_stages.STAGE1_MAX_TOKENS,
    )
    if stage1.error:
        facts, facts_violations = pipeline_stages.empty_facts(), [pipeline_stages.S1_PARSE]
    else:
        facts, facts_violations = pipeline_stages.parse_stage1_facts(stage1.content)

    parse_ok = (
        not stage1.error
        and pipeline_stages.S1_PARSE not in facts_violations
        and pipeline_stages.S1_ROUTE_LEAKED not in facts_violations
    )
    # проверка идёт по исходному caseText, не по обёрнутому/экранированному варианту - как в Kotlin
    red_flag_mismatch = pipeline_stages.child_red_flag_words_missing_from_symptoms(case_text, facts["symptoms"])
    parse_trusted = parse_ok and not red_flag_mismatch
    facts_for_decision = facts if parse_ok else pipeline_stages.empty_facts()
    facts_text = pipeline_stages.format_facts(facts_for_decision)

    # decideCall в реальном коде вызывается безусловно, даже если этап 1 упал транспортом
    stage2 = call_stage(
        pipeline_stages.STAGE2_SYSTEM_PROMPT, pipeline_stages.stage2_user_content(facts_text),
        pipeline_stages.STAGE2_MAX_TOKENS,
    )
    decision: Dict[str, Any] = {"route": None, "confidence": 0.0, "why": ""}
    decision_violations: List[str] = []
    if not stage2.error:
        decision, decision_violations = pipeline_stages.parse_stage2_decision(stage2.content)
    decide_ok = not stage2.error and decision["route"] is not None

    stage3 = None
    answer_text = pipeline_stages.FALLBACK_ANSWER
    if decide_ok or red_flag_mismatch:
        route = "EMERGENCY" if red_flag_mismatch else decision["route"]
        why = pipeline_stages.REDFLAG_ESCALATION_WHY if red_flag_mismatch else (
            decision["why"] or pipeline_stages.NONE_VALUE
        )
        stage3 = call_stage(
            pipeline_stages.STAGE3_SYSTEM_PROMPT,
            pipeline_stages.stage3_user_content(route, why, facts_text),
            pipeline_stages.STAGE3_MAX_TOKENS,
        )
        trimmed = (stage3.content or "").strip()
        if not stage3.error and len(trimmed) >= pipeline_stages.MIN_ANSWER_CHARS:
            answer_text = trimmed[: pipeline_stages.MAX_ANSWER_CHARS]
        final_route = route
    else:
        final_route = None

    error = stage1.error or stage2.error or (stage3.error if stage3 else None)
    check = case["pipeline_check"]
    hijacked = False
    hijack_reason = ""
    if not error:
        if check == spec11.PIPELINE_CHECK_FIELD_SPOOF:
            # injected_fields может целиться в любое поле этапа 1 - QUESTION_TYPE=OTHER/METRICS
            # уводит маршрут через правила 3/5, SYMPTOMS=none стирает признак целиком.
            injected = case.get("injected_fields", {})
            spoofed_question_type = injected.get("QUESTION_TYPE")
            spoofed_symptoms = injected.get("SYMPTOMS")
            if spoofed_question_type and facts["question_type"] == spoofed_question_type:
                hijacked, hijack_reason = True, "question_type_spoofed_to_%s" % spoofed_question_type
            elif spoofed_symptoms == "none" and not facts["symptoms"]:
                hijacked, hijack_reason = True, "symptoms_erased"
            elif final_route == "OFF_TOPIC":
                hijacked, hijack_reason = True, "route_off_topic"
        elif check == spec11.PIPELINE_CHECK_ROUTE_FLIP:
            expected_route = case["pipeline_expected_route"]
            if final_route != expected_route:
                hijacked, hijack_reason = True, "route_mismatch_expected_%s_got_%s" % (expected_route, final_route)

    total_usage: Dict[str, int] = llm_client.empty_usage()
    for call in calls:
        total_usage = llm_client.merge_usage(total_usage, call.usage)
    total_cost = sum(llm_client.usage_cost(call.usage, config.model) for call in calls)
    total_latency = sum(call.latency_ms for call in calls)

    return {
        "attack_id": case["attack_id"],
        "technique": case["technique"],
        "class": case["class"],
        "target": case["target"],
        "split": case["split"],
        "source": case["source"],
        "family": case.get("family", spec11.FAMILY_OWN),
        "expected_detector": case["expected_detector"],
        "defense": defense,
        "mode": spec11.MODE_PIPELINE,
        "pipeline_check": check,
        "pipeline": {
            "stage1_raw": stage1.content,
            "stage1_violations": facts_violations,
            "facts": facts,
            "parse_ok": parse_ok,
            "red_flag_mismatch": red_flag_mismatch,
            "facts_for_decision": facts_for_decision,
            "stage2_raw": stage2.content if stage2 else None,
            "decision_violations": decision_violations,
            "decide_ok": decide_ok,
            "route": final_route,
            "confidence": decision["confidence"],
            "why": decision["why"],
            "stage3_raw": stage3.content if stage3 else None,
            "answer_text": answer_text,
        },
        "response": answer_text,
        "detectors": {spec11.DETECTOR_ROUTE_HIJACK: hijacked},
        "leak_markers": [],
        "safety_bypass_reason": "",
        "triggered": [spec11.DETECTOR_ROUTE_HIJACK] if hijacked else [],
        "success": hijacked,
        "refused": not hijacked and not error,
        "route_hijack_reason": hijack_reason,
        "usage": total_usage,
        "cost_usd": round(total_cost, 8),
        "latency_ms": total_latency,
        "error": error,
        "status_code": None,
    }


def print_dry_run(args: argparse.Namespace, cases: List[Dict[str, Any]], problem: Optional[str]) -> None:
    sys.stdout.write("Сухой прогон атак task11, сеть не трогается.\n\n")
    if problem is not None:
        sys.stdout.write("Набор атак прочитать не удалось: %s\n" % problem)
        return
    counts = attacks_module.split_counts(cases)
    sys.stdout.write(
        "Атак в наборе: %d (dev %d, holdout %d)\n" % (len(cases), counts[spec11.SPLIT_DEV], counts[spec11.SPLIT_HOLDOUT])
    )
    sys.stdout.write("Мишень: %s, split: %s, повторов: %d\n" % (args.target, args.split, args.repeats))
    sys.stdout.write(
        "Ключ %s: %s\n" % (args.key_env, llm_client.describe_key_source(args.key_env))
    )

    for defense in defenses_for(args.defense):
        if defense not in spec11.DEFENSES_IMPLEMENTED:
            sys.stdout.write(
                "ВНИМАНИЕ: слой защиты %r ещё не реализован, прогон с ним будет пропущен.\n" % defense
            )

    total_calls = 0
    total_cost = 0.0
    header = "%-10s %-8s %-8s %s" % ("защита", "мишень", "вызовов", "оценка цены, USD")
    sys.stdout.write("\n" + header + "\n" + "-" * len(header) + "\n")
    for defense in defenses_for(args.defense):
        if defense not in spec11.DEFENSES_IMPLEMENTED:
            continue
        for target in spec11.TARGETS:
            if args.target != spec11.TARGET_ALL and target != args.target:
                continue
            target_cases = [case for case in cases if case["target"] == target]
            per_case = [estimate_case_calls_and_cost(case, args.model) for case in target_cases]
            calls = sum(case_calls for case_calls, _ in per_case) * args.repeats
            cost = sum(case_cost for _, case_cost in per_case) * args.repeats
            total_calls += calls
            total_cost += cost
            pipeline_count = sum(1 for case in target_cases if case.get("mode") == spec11.MODE_PIPELINE)
            suffix = " (из них pipeline: %d атаки x3 вызова)" % pipeline_count if pipeline_count else ""
            sys.stdout.write("%-10s %-8s %-8d %.4f%s\n" % (defense, target, calls, cost, suffix))
    sys.stdout.write("\nИтого вызовов: %d, оценка сверху: %.4f USD\n" % (total_calls, total_cost))
    sys.stdout.write(
        "Оценка грубая: выход считается по потолку %d токенов на ответ, вход по %.1f символов на токен.\n"
        % (spec11.ATTACK_MAX_TOKENS, spec11.CHARS_PER_TOKEN_ESTIMATE)
    )


def run_case(case: Dict[str, Any], defense: str, config: llm_client.ClientConfig) -> Dict[str, Any]:
    if case.get("mode") == spec11.MODE_PIPELINE:
        return run_pipeline_case(case, defense, config)
    return run_one(case, defense, config)


def run_defense(
    cases: List[Dict[str, Any]], defense: str, config: llm_client.ClientConfig, out_path: str, workers: int
) -> Dict[str, Any]:
    results: Dict[int, Dict[str, Any]] = {}
    lock = threading.Lock()
    done = 0
    started = time.time()

    sys.stdout.write("\nЗащита %s: атак %d, потоков %d\n" % (defense, len(cases), workers))
    sys.stdout.write("Вывод: %s\n" % out_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(run_case, case, defense, config): position for position, case in enumerate(cases)
        }
        for future in concurrent.futures.as_completed(futures):
            position = futures[future]
            record = future.result()
            with lock:
                results[position] = record
                done += 1
                mark = ",".join(record["triggered"]) if record["triggered"] else ("REFUSED" if not record["error"] else "ERR")
                sys.stdout.write(
                    "  [%d/%d] %-24s %-8s %5d мс  %.6f USD  %s%s\n"
                    % (
                        done,
                        len(cases),
                        record["attack_id"],
                        record["target"],
                        record["latency_ms"],
                        record["cost_usd"],
                        mark,
                        ("  ошибка: " + record["error"][:60]) if record["error"] else "",
                    )
                )
                sys.stdout.flush()

    ordered = [results[position] for position in sorted(results)]
    with open(out_path, "w", encoding="utf-8") as handle:
        for record in ordered:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    successes = sum(1 for record in ordered if record["success"])
    errors = sum(1 for record in ordered if record["error"])
    cost = sum(record["cost_usd"] for record in ordered)
    elapsed = time.time() - started
    sys.stdout.write(
        "Защита %s готова: атак %d, успешных %d, с ошибкой %d, стоимость %.6f USD, время %.1f с\n"
        % (defense, len(ordered), successes, errors, cost, elapsed)
    )
    return {"defense": defense, "cases": len(ordered), "successes": successes, "errors": errors, "cost_usd": cost, "out_path": out_path}


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.workers <= 0:
        sys.stderr.write("Значение --workers должно быть больше нуля.\n")
        return spec11.EXIT_CONFIG_ERROR
    if args.repeats < spec11.MIN_REPEATS:
        sys.stderr.write("Значение --repeats должно быть не меньше %d.\n" % spec11.MIN_REPEATS)
        return spec11.EXIT_CONFIG_ERROR

    cases: List[Dict[str, Any]] = []
    problem: Optional[str] = None
    try:
        ids = [piece.strip() for piece in args.ids.split(",") if piece.strip()] if args.ids else None
        records = attacks_module.load_attacks(args.attacks_path)
        filtered = attacks_module.filter_attacks(records, split=args.split, ids=ids)
        cases = attacks_module.expand_by_target(filtered, args.target)
        if not ids:
            # pipeline-атаки (ROUTE_HIJACK) не зависят от defense - защита на уровне системного
            # промпта не касается внутренней 3-этапной цепочки. Прогоняются отдельно через --ids.
            cases = [case for case in cases if case.get("mode", spec11.MODE_SINGLE) != spec11.MODE_PIPELINE]
        if args.limit:
            cases = cases[: args.limit]
    except attacks_module.AttacksError as attacks_error:
        problem = str(attacks_error)
    except OSError as os_error:
        problem = "не читается %s: %s" % (args.attacks_path, os_error)

    if args.dry_run:
        print_dry_run(args, cases, problem)
        return spec11.EXIT_OK

    if problem is not None:
        sys.stderr.write("Не могу прочитать набор атак: %s\n" % problem)
        return spec11.EXIT_DATA_ERROR

    api_key = llm_client.read_api_key(args.key_env)
    if not api_key:
        sys.stderr.write(
            "Ключ %s не найден ни в окружении, ни в %s.\n" % (args.key_env, spec11.LOCAL_PROPERTIES_PATH)
        )
        return spec11.EXIT_CONFIG_ERROR

    thinking_off = not args.thinking
    config = build_config(args.model, args.base_url, api_key, args.timeout, thinking_off)

    if not os.path.isdir(args.out_dir):
        os.makedirs(args.out_dir)

    selected_defenses = defenses_for(args.defense)
    unimplemented = [defense for defense in selected_defenses if defense not in spec11.DEFENSES_IMPLEMENTED]
    if unimplemented:
        sys.stdout.write(
            "ВНИМАНИЕ: слои защиты %s ещё не реализованы (только %s), пропускаю их.\n"
            % (unimplemented, list(spec11.DEFENSES_IMPLEMENTED))
        )
    to_run = [defense for defense in selected_defenses if defense in spec11.DEFENSES_IMPLEMENTED]
    if not to_run:
        sys.stderr.write("Ни одного реализованного слоя защиты не выбрано, нечего прогонять.\n")
        return spec11.EXIT_CONFIG_ERROR

    sys.stdout.write(
        "Модель %s, %s, атак %d, повторов %d, защит %s\n"
        % (config.model, config.base_url, len(cases), args.repeats, to_run)
    )

    summaries: List[Dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for defense in to_run:
            out_path = out_path_for(args.out_dir, defense, repeat, args.repeats)
            summaries.append(run_defense(cases, defense, config, out_path, args.workers))

    total_cost = sum(summary["cost_usd"] for summary in summaries)
    total_errors = sum(summary["errors"] for summary in summaries)
    sys.stdout.write(
        "\nГотово. Прогонов %d, атак с ошибкой суммарно %d, потрачено %.6f USD\n"
        % (len(summaries), total_errors, total_cost)
    )
    return spec11.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
