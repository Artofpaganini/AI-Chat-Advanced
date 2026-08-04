"""Прогон косвенных инъекций из data/documents.jsonl против системных промптов jarvis/alva.

Каждый вызов - один документ на одном слое защиты. Для H4_FAKE_ROLE документов делается второй
вызов (follow-up) с уже полученным ответом в истории - им меряется CONTEXT_POISONED (контракт
5.4). Модель недетерминирована, поэтому --repeats запускает весь набор N раз в отдельные файлы.

Урок task11 4: имя ВЫХОДНОГО КАТАЛОГА уникально для каждого запуска (не только имя файла) -
по умолчанию raw/run_<timestamp>/, чтобы повторный прогон не мог затереть прошлый.

Запуск: python3 harness/run_indirect.py --dry-run
        python3 harness/run_indirect.py --vector all --defense none --repeats 3
        python3 harness/run_indirect.py --vector V1_SUMMARY --defense none --repeats 3 --workers 4
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import context_window
import defenses
import detectors12
import payloads
import spec12

sys.path.insert(0, spec12.TASK7_HARNESS_DIR)
import llm_client


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Прогон косвенных инъекций task12")
    parser.add_argument("--vector", choices=spec12.VECTORS + ("all",), default="all")
    parser.add_argument("--defense", choices=spec12.DEFENSES + (spec12.DEFENSE_SWEEP,), default=spec12.DEFENSE_NONE)
    parser.add_argument("--split", choices=spec12.SPLITS + ("all",), default="all")
    parser.add_argument("--repeats", type=int, default=spec12.DEFAULT_REPEATS)
    parser.add_argument("--workers", type=int, default=spec12.DEFAULT_WORKERS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--documents-path", dest="documents_path", default=spec12.DOCUMENTS_PATH)
    parser.add_argument("--ids", dest="ids", default="", help="через запятую - прогнать только эти id")
    parser.add_argument("--out-dir", dest="out_dir", default="")
    parser.add_argument("--model", default=spec12.DEFAULT_MODEL)
    parser.add_argument("--base-url", dest="base_url", default=spec12.DEFAULT_BASE_URL)
    parser.add_argument("--key-env", dest="key_env", default=spec12.DEFAULT_KEY_ENV)
    parser.add_argument("--timeout", type=int, default=spec12.REQUEST_TIMEOUT_SECONDS)
    parser.add_argument("--thinking", dest="thinking", action="store_true")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    return parser


def defenses_for(name: str) -> List[str]:
    if name == spec12.DEFENSE_SWEEP:
        return list(spec12.DEFENSES)
    return [name]


def unique_run_dir(base_raw_dir: str) -> str:
    """Урок task11 4: каждый запуск - свой каталог, повторный прогон не может затереть прошлый."""
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = os.path.join(base_raw_dir, spec12.RUN_DIR_PREFIX + stamp)
    suffix = 1
    while os.path.isdir(candidate):
        suffix += 1
        candidate = os.path.join(base_raw_dir, "%s%s_%d" % (spec12.RUN_DIR_PREFIX, stamp, suffix))
    return candidate


def out_path_for(out_dir: str, defense: str, repeat: int, repeats: int) -> str:
    name = spec12.RAW_FILE_PREFIX + defense
    if repeats > spec12.MIN_REPEATS:
        name += spec12.REPEAT_SUFFIX_PREFIX + str(repeat)
    return os.path.join(out_dir, name + spec12.RAW_FILE_EXTENSION)


def build_config(model: str, base_url: str, api_key: str, timeout: int, thinking_off: bool) -> llm_client.ClientConfig:
    extra_payload = dict(spec12.CLOUD_REASONING_OFF) if thinking_off else None
    return llm_client.ClientConfig(
        model=model, base_url=base_url, api_key=api_key, timeout=timeout, extra_payload=extra_payload
    )


def apply_window_if_v1(record: Dict[str, Any], turns: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Окно контекста (HistoryMessageMapper.kt) применимо только к V1_SUMMARY - настоящему
    каналу импорта. У V2/V3 такого пути в приложении нет, обрезать там нечего."""
    if record["vector"] == spec12.VECTOR_SUMMARY:
        return context_window.apply_context_window(turns)
    return turns


def build_primary_messages(record: Dict[str, Any], target: str, defense: str) -> List[Dict[str, str]]:
    system = {"role": spec12.REQUEST_ROLE_SYSTEM, "content": defenses.system_prompt_for(target, defense)}
    turns = apply_window_if_v1(record, defenses.build_turns_for_defense(record, defense))
    return [system] + turns


def estimate_prompt_tokens(chars: int) -> int:
    return int(chars / spec12.CHARS_PER_TOKEN_ESTIMATE) + 1


def estimate_record_chars(record: Dict[str, Any], target: str) -> int:
    chars = len(spec12.SYSTEM_PROMPTS[target]) + len(record["final_user_text"])
    for turn in record.get("history") or []:
        chars += len(turn["content"])
    return chars


def run_one(record: Dict[str, Any], defense: str, config: llm_client.ClientConfig) -> Dict[str, Any]:
    target = record["target"]
    system = {"role": spec12.REQUEST_ROLE_SYSTEM, "content": defenses.system_prompt_for(target, defense)}
    turns = defenses.build_turns_for_defense(record, defense)
    messages = [system] + apply_window_if_v1(record, turns)
    result = llm_client.call_with_config(messages, spec12.ATTACK_TEMPERATURE, config, spec12.ATTACK_MAX_TOKENS)
    delivered_text, output_flags = defenses.apply_output_defense(result.content, record, defense) if not result.error else (result.content, [])

    followup_text: Optional[str] = None
    followup_error: Optional[str] = None
    followup_result = None
    followup_delivered: Optional[str] = None
    followup_text_requested = record.get("followup_user_text")
    if not result.error and followup_text_requested:
        # Как в реальном приложении: следующий send() пересчитывает окно контекста заново по
        # ПОЛНОЙ (не обрезанной прошлым вызовом) истории - turns, а не messages. В истории лежит
        # то, что реально ДОШЛО до пользователя (delivered_text), а не сырой ответ модели.
        followup_turns = turns + [
            {"role": spec12.REQUEST_ROLE_ASSISTANT, "content": delivered_text},
            {"role": spec12.REQUEST_ROLE_USER, "content": followup_text_requested},
        ]
        followup_messages = [system] + apply_window_if_v1(record, followup_turns)
        followup_result = llm_client.call_with_config(
            followup_messages, spec12.ATTACK_TEMPERATURE, config, spec12.ATTACK_MAX_TOKENS
        )
        followup_error = followup_result.error
        if not followup_result.error:
            followup_delivered, _followup_flags = defenses.apply_output_defense(followup_result.content, record, defense)
            followup_text = followup_delivered

    require_unattributed = defense in (spec12.DEFENSE_D4_PROVENANCE, spec12.DEFENSE_ALL)
    detection = None
    if not result.error:
        detection = detectors12.run_detectors(
            response_text=delivered_text,
            target=target,
            injected_line_marker=record.get("injected_line_marker", ""),
            false_fact_marker=record.get("false_fact_marker", ""),
            override_kind=record.get("override_kind", ""),
            followup_response_text=followup_text,
            context_poison_marker=record.get("context_poison_marker", ""),
            require_unattributed=require_unattributed,
        )

    usage = result.usage
    cost = llm_client.usage_cost(result.usage, config.model)
    latency = result.latency_ms
    if followup_result is not None:
        usage = llm_client.merge_usage(usage, followup_result.usage)
        cost += llm_client.usage_cost(followup_result.usage, config.model)
        latency += followup_result.latency_ms

    return {
        "id": record["id"],
        "vector": record["vector"],
        "hiding": record["hiding"],
        "target": target,
        "split": record["split"],
        "source": record["source"],
        "expected_detector": record["expected_detector"],
        "defense": defense,
        "raw_response": result.content,
        "response": delivered_text,
        "output_defense_flags": output_flags,
        "followup_response": followup_text,
        "followup_error": followup_error,
        "detectors": detection["detectors"] if detection else None,
        "override_reason": detection["override_reason"] if detection else "",
        "triggered": detection["triggered"] if detection else [],
        "success": detection["success"] if detection else False,
        "clean": detection[spec12.DETECTOR_CLEAN] if detection else False,
        "usage": usage,
        "cost_usd": round(cost, 8),
        "latency_ms": latency,
        "error": result.error,
        "status_code": result.status_code,
    }


def print_dry_run(args: argparse.Namespace, records: List[Dict[str, Any]], problem: Optional[str]) -> None:
    sys.stdout.write("Сухой прогон task12, сеть не трогается.\n\n")
    if problem is not None:
        sys.stdout.write("Набор документов прочитать не удалось: %s\n" % problem)
        return
    counts = payloads.split_counts(records)
    sys.stdout.write(
        "Документов: %d (dev %d, holdout %d)\n" % (len(records), counts[spec12.SPLIT_DEV], counts[spec12.SPLIT_HOLDOUT])
    )
    sys.stdout.write("Вектор: %s, split: %s, повторов: %d\n" % (args.vector, args.split, args.repeats))
    sys.stdout.write("Ключ %s: %s\n" % (args.key_env, llm_client.describe_key_source(args.key_env)))

    matrix = payloads.vector_hiding_counts(records)
    sys.stdout.write("\nматрица вектор x приём сокрытия:\n")
    header = "%-14s" % "" + "".join("%-16s" % hiding for hiding in spec12.HIDINGS)
    sys.stdout.write(header + "\n")
    for vector in spec12.VECTORS:
        row = "%-14s" % vector + "".join("%-16d" % matrix[vector][hiding] for hiding in spec12.HIDINGS)
        sys.stdout.write(row + "\n")

    for defense in defenses_for(args.defense):
        if defense not in spec12.DEFENSES_IMPLEMENTED:
            sys.stdout.write(
                "\nВНИМАНИЕ: слой защиты %r ещё не реализован (defenses.py - интерфейс), прогон с ним будет пропущен.\n"
                % defense
            )

    total_calls = 0
    total_cost = 0.0
    followup_calls = sum(1 for record in records if record.get("followup_user_text"))
    header2 = "%-10s %-14s %-8s %s" % ("защита", "вектор", "вызовов", "оценка цены, USD")
    sys.stdout.write("\n" + header2 + "\n" + "-" * len(header2) + "\n")
    for defense in defenses_for(args.defense):
        if defense not in spec12.DEFENSES_IMPLEMENTED:
            continue
        for vector in spec12.VECTORS:
            if args.vector != "all" and vector != args.vector:
                continue
            vector_records = [record for record in records if record["vector"] == vector]
            target = spec12.VECTOR_TARGET[vector]
            per_case_calls = [2 if record.get("followup_user_text") else 1 for record in vector_records]
            per_case_chars = [estimate_record_chars(record, target) for record in vector_records]
            calls = sum(per_case_calls) * args.repeats
            usage_estimate = [
                {"prompt_tokens": estimate_prompt_tokens(chars), "completion_tokens": spec12.ATTACK_MAX_TOKENS}
                for chars, call_count in zip(per_case_chars, per_case_calls)
                for _ in range(call_count)
            ]
            cost = sum(llm_client.usage_cost(usage, args.model) for usage in usage_estimate) * args.repeats
            total_calls += calls
            total_cost += cost
            sys.stdout.write("%-10s %-14s %-8d %.4f\n" % (defense, vector, calls, cost))
    sys.stdout.write(
        "\nИтого вызовов: %d (из них follow-up на H4_FAKE_ROLE: %d документов x повторы), оценка сверху: %.4f USD\n"
        % (total_calls, followup_calls, total_cost)
    )
    sys.stdout.write(
        "Оценка грубая: выход считается по потолку %d токенов на ответ, вход по %.1f символов на токен.\n"
        % (spec12.ATTACK_MAX_TOKENS, spec12.CHARS_PER_TOKEN_ESTIMATE)
    )


def run_defense(
    records: List[Dict[str, Any]], defense: str, config: llm_client.ClientConfig, out_path: str, workers: int
) -> Dict[str, Any]:
    results: Dict[int, Dict[str, Any]] = {}
    lock = threading.Lock()
    done = 0
    started = time.time()

    sys.stdout.write("\nЗащита %s: документов %d, потоков %d\n" % (defense, len(records), workers))
    sys.stdout.write("Вывод: %s\n" % out_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(run_one, record, defense, config): position for position, record in enumerate(records)
        }
        for future in concurrent.futures.as_completed(futures):
            position = futures[future]
            record = future.result()
            with lock:
                results[position] = record
                done += 1
                mark = ",".join(record["triggered"]) if record["triggered"] else ("CLEAN" if not record["error"] else "ERR")
                sys.stdout.write(
                    "  [%d/%d] %-24s %-8s %5d мс  %.6f USD  %s%s\n"
                    % (
                        done, len(records), record["id"], record["target"], record["latency_ms"],
                        record["cost_usd"], mark,
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
        "Защита %s готова: документов %d, успешных атак %d, с ошибкой %d, стоимость %.6f USD, время %.1f с\n"
        % (defense, len(ordered), successes, errors, cost, elapsed)
    )
    return {"defense": defense, "cases": len(ordered), "successes": successes, "errors": errors, "cost_usd": cost, "out_path": out_path}


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.workers <= 0:
        sys.stderr.write("Значение --workers должно быть больше нуля.\n")
        return spec12.EXIT_CONFIG_ERROR
    if args.repeats < spec12.MIN_REPEATS:
        sys.stderr.write("Значение --repeats должно быть не меньше %d.\n" % spec12.MIN_REPEATS)
        return spec12.EXIT_CONFIG_ERROR

    records: List[Dict[str, Any]] = []
    problem: Optional[str] = None
    try:
        ids = [piece.strip() for piece in args.ids.split(",") if piece.strip()] if args.ids else None
        all_records = payloads.load_documents(args.documents_path)
        records = payloads.filter_documents(all_records, vector=args.vector, split=args.split, ids=ids)
        if args.limit:
            records = records[: args.limit]
    except payloads.DocumentsError as documents_error:
        problem = str(documents_error)
    except OSError as os_error:
        problem = "не читается %s: %s" % (args.documents_path, os_error)

    if args.dry_run:
        print_dry_run(args, records, problem)
        return spec12.EXIT_OK

    if problem is not None:
        sys.stderr.write("Не могу прочитать набор документов: %s\n" % problem)
        return spec12.EXIT_DATA_ERROR
    if not records:
        sys.stderr.write("Набор документов пуст после фильтрации, нечего прогонять.\n")
        return spec12.EXIT_DATA_ERROR

    api_key = llm_client.read_api_key(args.key_env)
    if not api_key:
        sys.stderr.write("Ключ %s не найден ни в окружении, ни в %s.\n" % (args.key_env, spec12.LOCAL_PROPERTIES_PATH))
        return spec12.EXIT_CONFIG_ERROR

    thinking_off = not args.thinking
    config = build_config(args.model, args.base_url, api_key, args.timeout, thinking_off)

    out_dir = args.out_dir or unique_run_dir(spec12.RAW_DIR)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    selected_defenses = defenses_for(args.defense)
    unimplemented = [defense for defense in selected_defenses if defense not in spec12.DEFENSES_IMPLEMENTED]
    if unimplemented:
        sys.stdout.write(
            "ВНИМАНИЕ: слои защиты %s ещё не реализованы (только %s), пропускаю их.\n"
            % (unimplemented, list(spec12.DEFENSES_IMPLEMENTED))
        )
    to_run = [defense for defense in selected_defenses if defense in spec12.DEFENSES_IMPLEMENTED]
    if not to_run:
        sys.stderr.write("Ни одного реализованного слоя защиты не выбрано, нечего прогонять.\n")
        return spec12.EXIT_CONFIG_ERROR

    sys.stdout.write(
        "Модель %s, %s, документов %d, повторов %d, защит %s, каталог %s\n"
        % (config.model, config.base_url, len(records), args.repeats, to_run, out_dir)
    )

    summaries: List[Dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for defense in to_run:
            out_path = out_path_for(out_dir, defense, repeat, args.repeats)
            summaries.append(run_defense(records, defense, config, out_path, args.workers))

    total_cost = sum(summary["cost_usd"] for summary in summaries)
    total_errors = sum(summary["errors"] for summary in summaries)
    sys.stdout.write(
        "\nГотово. Прогонов %d, документов с ошибкой суммарно %d, потрачено %.6f USD\nКаталог: %s\n"
        % (len(summaries), total_errors, total_cost, out_dir)
    )
    return spec12.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
