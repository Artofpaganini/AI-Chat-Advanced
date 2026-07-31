"""Прогон трёх режимов: only_llm, only_micro, cascade. Сырьё пишется в raw/.

Уровень 1 - micro_model.predict, локально, ноль денег.
Уровень 2 - pipeline.run_baseline из task7: один вызов deepseek, разбор ответа, подсчёт денег.

Запуск:
  python3 harness/run_pipeline.py --dry-run --mode all
  python3 harness/run_pipeline.py --mode all --repeats 3
  python3 harness/run_pipeline.py --parity-only
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import micro_model
import spec10

sys.path.insert(0, spec10.TASK7_HARNESS_DIR)

import llm_client
import pipeline
import run_eval
import spec7

SOURCE_MICRO = "micro"
SOURCE_LLM = "llm"


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def modes_for(name: str) -> List[str]:
    if name == spec10.MODE_ALL:
        return list(spec10.MODES)
    return [name]


def out_path_for(out_dir: str, mode: str, repeat: int) -> str:
    suffix = "" if repeat <= 1 else spec10.REPEAT_SUFFIX_PREFIX + str(repeat)
    name = spec10.RAW_FILE_PREFIX + mode + suffix + spec10.RAW_FILE_EXTENSION
    return os.path.join(out_dir, name)


def llm_config(model: str, base_url: str, key_env: str, timeout: int) -> llm_client.ClientConfig:
    location = llm_client.inference_location(base_url)
    api_key = "" if location == spec7.LOCATION_LOCAL else llm_client.read_api_key(key_env)
    return llm_client.ClientConfig(
        model=model, base_url=base_url, api_key=api_key, timeout=timeout, extra_payload=None
    )


def micro_block(prediction: micro_model.Prediction, micro_ms: float) -> Dict[str, Any]:
    return {
        "label": prediction.label,
        "prob": round(prediction.prob, 6),
        "margin": round(prediction.margin, 6),
        "status": prediction.status,
        "probs": [round(value, 6) for value in prediction.probs],
        "latency_ms": round(micro_ms, 4),
    }


def llm_block(decision: pipeline.Decision) -> Dict[str, Any]:
    return {
        "route": decision.route,
        "confidence": decision.confidence_final,
        "latency_ms": decision.latency_ms,
        "cost_usd": round(decision.cost_usd, 8),
        "calls": decision.calls,
        "model": decision.model,
        "error": decision.error,
    }


def predict_micro(text: str, model: micro_model.MicroModel):
    started = time.perf_counter()
    prediction = micro_model.predict(text, model)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return prediction, elapsed_ms


def base_record(case: Dict[str, Any], mode: str, repeat: int) -> Dict[str, Any]:
    return {
        "case_id": case.get("id"),
        "group": case.get("group"),
        "expected_route": case.get("expected_route"),
        "expected_status": case.get("expected_status"),
        "mode": mode,
        "repeat": repeat,
    }


def run_only_llm(
    case: Dict[str, Any], repeat: int, config: llm_client.ClientConfig
) -> Dict[str, Any]:
    started = time.time()
    decision = pipeline.run_baseline(str(case.get("text", "")), config, str(case.get("id", "")))
    record = base_record(case, spec10.MODE_ONLY_LLM, repeat)
    record.update(
        {
            "micro": None,
            "escalated": True,
            "llm": llm_block(decision),
            "final_route": decision.route,
            "final_source": SOURCE_LLM,
            "llm_calls": decision.calls,
            "latency_ms": int((time.time() - started) * 1000),
            "cost_usd": round(decision.cost_usd, 8),
            "error": decision.error,
        }
    )
    return record


def run_only_micro(
    case: Dict[str, Any], repeat: int, model: micro_model.MicroModel
) -> Dict[str, Any]:
    started = time.time()
    prediction, micro_ms = predict_micro(str(case.get("text", "")), model)
    record = base_record(case, spec10.MODE_ONLY_MICRO, repeat)
    record.update(
        {
            "micro": micro_block(prediction, micro_ms),
            "escalated": False,
            "llm": None,
            "final_route": prediction.label,
            "final_source": SOURCE_MICRO,
            "llm_calls": 0,
            "latency_ms": int((time.time() - started) * 1000),
            "latency_precise_ms": round(micro_ms, 4),
            "cost_usd": 0.0,
            "error": None,
        }
    )
    return record


def severity_of(route: Optional[str]) -> int:
    return spec10.SEVERITY.get(route or "", -1)


def merge_routes(
    micro_label: str, llm_route: Optional[str], rule: str
) -> Tuple[Optional[str], str, Optional[str]]:
    """Раздел 5.1 контракта: слияние только вверх. Старое правило оставлено для сравнения."""
    if llm_route is None:
        return micro_label, SOURCE_MICRO, "большая модель не дала маршрут, итог взят от micro-model"
    if rule == spec10.MERGE_SEVERITY_MAX and severity_of(micro_label) > severity_of(llm_route):
        return micro_label, SOURCE_MICRO, None
    return llm_route, SOURCE_LLM, None


def run_cascade(
    case: Dict[str, Any],
    repeat: int,
    model: micro_model.MicroModel,
    config: llm_client.ClientConfig,
    mode: str = spec10.MODE_CASCADE,
) -> Dict[str, Any]:
    started = time.time()
    text = str(case.get("text", ""))
    prediction, micro_ms = predict_micro(text, model)
    record = base_record(case, mode, repeat)
    if prediction.status == spec10.STATUS_OK:
        record.update(
            {
                "micro": micro_block(prediction, micro_ms),
                "escalated": False,
                "llm": None,
                "final_route": prediction.label,
                "final_source": SOURCE_MICRO,
                "llm_calls": 0,
                "latency_ms": int((time.time() - started) * 1000),
                "latency_precise_ms": round(micro_ms, 4),
                "cost_usd": 0.0,
                "error": None,
            }
        )
        return record
    decision = pipeline.run_baseline(text, config, str(case.get("id", "")))
    final_route, final_source, fallback_note = merge_routes(
        prediction.label, decision.route, spec10.MODE_MERGE_RULE[mode]
    )
    record.update(
        {
            "micro": micro_block(prediction, micro_ms),
            "escalated": True,
            "llm": llm_block(decision),
            "final_route": final_route,
            "final_source": final_source,
            "llm_calls": decision.calls,
            "latency_ms": int((time.time() - started) * 1000),
            "cost_usd": round(decision.cost_usd, 8),
            "error": decision.error or fallback_note,
        }
    )
    return record


def run_case(
    case: Dict[str, Any],
    mode: str,
    repeat: int,
    model: micro_model.MicroModel,
    config: llm_client.ClientConfig,
) -> Dict[str, Any]:
    try:
        if mode == spec10.MODE_ONLY_LLM:
            return run_only_llm(case, repeat, config)
        if mode == spec10.MODE_ONLY_MICRO:
            return run_only_micro(case, repeat, model)
        return run_cascade(case, repeat, model, config, mode)
    except Exception as unexpected_error:
        record = base_record(case, mode, repeat)
        record.update(
            {
                "micro": None,
                "escalated": False,
                "llm": None,
                "final_route": None,
                "final_source": None,
                "llm_calls": 0,
                "latency_ms": 0,
                "cost_usd": 0.0,
                "error": "сбой кейса: %s" % unexpected_error,
            }
        )
        return record


def run_mode(
    cases: List[Dict[str, Any]],
    mode: str,
    repeat: int,
    model: micro_model.MicroModel,
    config: llm_client.ClientConfig,
    workers: int,
    out_dir: str,
) -> str:
    if mode == spec10.MODE_ONLY_MICRO or workers <= 1:
        records = [run_case(case, mode, repeat, model, config) for case in cases]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(run_case, case, mode, repeat, model, config) for case in cases
            ]
            records = [future.result() for future in futures]
    path = out_path_for(out_dir, mode, repeat)
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def write_parity(
    cases: List[Dict[str, Any]], model: micro_model.MicroModel, path: str
) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    for case in cases:
        prediction = micro_model.predict(str(case.get("text", "")), model)
        entries.append(
            {
                "id": case.get("id"),
                "label": prediction.label,
                "prob": prediction.prob,
                "margin": prediction.margin,
                "status": prediction.status,
                "probs": list(prediction.probs),
            }
        )
    document = {
        "format_version": spec10.FORMAT_VERSION,
        "labels": list(model.labels),
        "cases": os.path.relpath(spec10.CASES_PATH, spec10.CHALLENGE_DIR),
        "tolerance": 1e-6,
        "count": len(entries),
        "entries": entries,
    }
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return document


def escalation_forecast(
    cases: List[Dict[str, Any]], model: micro_model.MicroModel
) -> Dict[str, Any]:
    """Micro-model локальна и детерминирована, поэтому число эскалаций известно до сети."""
    escalated = 0
    by_reason = {"always_escalate": 0, "low_confidence": 0}
    for case in cases:
        prediction = micro_model.predict(str(case.get("text", "")), model)
        if prediction.status != spec10.STATUS_OK:
            escalated += 1
            if prediction.label in model.always_escalate_labels:
                by_reason["always_escalate"] += 1
            else:
                by_reason["low_confidence"] += 1
    return {"escalated": escalated, "stayed": len(cases) - escalated, "by_reason": by_reason}


def estimate_cost(cases: List[Dict[str, Any]], model_name: str, calls: int) -> float:
    if not cases or calls <= 0:
        return 0.0
    prompt_tokens = [
        run_eval.estimate_prompt_tokens(str(case.get("text", "")), spec7.TRIAGE_SYSTEM_PROMPT)
        for case in cases
    ]
    average_prompt = sum(prompt_tokens) / len(prompt_tokens)
    usage = {
        "prompt_tokens": int(average_prompt * calls),
        "completion_tokens": int(spec7.MAX_TOKENS * 0.4 * calls),
    }
    return round(llm_client.usage_cost(usage, model_name), 6)


def print_dry_run(
    args: argparse.Namespace,
    cases: List[Dict[str, Any]],
    model: micro_model.MicroModel,
    modes: List[str],
) -> None:
    forecast = escalation_forecast(cases, model)
    print("План прогона, сеть не трогается")
    print("  кейсов: %d" % len(cases))
    print("  повторов на режим: %d" % args.repeats)
    print("  модель верхнего уровня: %s" % args.model_name)
    print("  ключ: %s" % llm_client.describe_key_source(args.key_env))
    print("  файл весов: %s (%d признаков)" % (args.model_path, model.vocabulary.size()))
    print(
        "  пороги: prob >= %.2f, margin >= %.2f, всегда наверх: %s"
        % (
            model.confident_min_prob,
            model.confident_min_margin,
            ", ".join(model.always_escalate_labels),
        )
    )
    total_calls = 0
    total_cost = 0.0
    print("")
    print("  режим            вызовов LLM за прогон   всего за %d повторов" % args.repeats)
    for mode in modes:
        if mode == spec10.MODE_ONLY_LLM:
            per_run = len(cases)
        elif mode == spec10.MODE_ONLY_MICRO:
            per_run = 0
        else:
            per_run = forecast["escalated"]
        calls = per_run * args.repeats
        total_calls += calls
        total_cost += estimate_cost(cases, args.model_name, calls)
        print("  %-16s %-23d %d" % (mode, per_run, calls))
    print("")
    print(
        "  прогноз каскада: %d наверх, %d закрывает micro-model"
        % (forecast["escalated"], forecast["stayed"])
    )
    print(
        "    из них принудительных EMERGENCY: %d, по низкой уверенности: %d"
        % (forecast["by_reason"]["always_escalate"], forecast["by_reason"]["low_confidence"])
    )
    print("  всего вызовов LLM: %d" % total_calls)
    print("  оценка стоимости: %.6f USD (грубая, по средней длине промпта)" % total_cost)
    print("")
    print("  файлы, которые появятся:")
    for mode in modes:
        for repeat in range(1, args.repeats + 1):
            print("    %s" % os.path.relpath(out_path_for(args.out_dir, mode, repeat), os.getcwd()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Прогон каскада micro-model -> LLM")
    parser.add_argument(
        "--mode", default=spec10.MODE_ALL, choices=list(spec10.MODES) + [spec10.MODE_ALL]
    )
    parser.add_argument("--repeats", type=int, default=spec10.DEFAULT_REPEATS)
    parser.add_argument("--cases", dest="cases_path", default=spec10.CASES_PATH)
    parser.add_argument("--model-file", dest="model_path", default=spec10.MODEL_PATH)
    parser.add_argument("--out-dir", dest="out_dir", default=spec10.RAW_DIR)
    parser.add_argument("--parity", dest="parity_path", default=spec10.PARITY_PATH)
    parser.add_argument("--workers", type=int, default=spec10.DEFAULT_WORKERS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--parity-only", dest="parity_only", action="store_true")
    parser.add_argument("--model-name", dest="model_name", default=spec10.LLM_MODEL)
    parser.add_argument("--base-url", dest="base_url", default=spec10.LLM_BASE_URL)
    parser.add_argument("--key-env", dest="key_env", default=spec10.LLM_KEY_ENV)
    parser.add_argument("--timeout", type=int, default=spec7.REQUEST_TIMEOUT_SECONDS)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.repeats < spec10.MIN_REPEATS:
        print("повторов должно быть не меньше %d" % spec10.MIN_REPEATS)
        return 2
    if not os.path.isfile(args.model_path):
        print("нет файла весов %s, сначала запустите train_micro.py" % args.model_path)
        return 2
    if not os.path.isfile(args.cases_path):
        print("нет набора кейсов %s" % args.cases_path)
        return 2

    try:
        model = micro_model.load_model(args.model_path)
    except micro_model.InvalidWeightsError as invariant_error:
        print("веса негодны, micro-model недоступна: %s" % invariant_error)
        print("режимы с micro-model запускать нельзя, весь трафик должен идти в большую модель")
        return 3
    cases = read_jsonl(args.cases_path)
    if args.limit > 0:
        cases = cases[: args.limit]

    if args.parity_only:
        document = write_parity(cases, model, args.parity_path)
        print("паритет-файл записан: %s, кейсов %d" % (args.parity_path, document["count"]))
        return 0

    modes = modes_for(args.mode)
    if args.dry_run:
        print_dry_run(args, cases, model, modes)
        return 0

    config = llm_config(args.model_name, args.base_url, args.key_env, args.timeout)
    needs_key = any(spec10.MODE_USES_LLM[mode] for mode in modes)
    if needs_key and not config.api_key and not config.is_local:
        print("ключ не найден: %s" % llm_client.describe_key_source(args.key_env))
        return 2

    document = write_parity(cases, model, args.parity_path)
    print("паритет-файл: %s, кейсов %d" % (args.parity_path, document["count"]))

    for mode in modes:
        for repeat in range(1, args.repeats + 1):
            started = time.time()
            path = run_mode(cases, mode, repeat, model, config, args.workers, args.out_dir)
            print(
                "%s повтор %d -> %s за %.1f с"
                % (mode, repeat, os.path.basename(path), time.time() - started)
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
