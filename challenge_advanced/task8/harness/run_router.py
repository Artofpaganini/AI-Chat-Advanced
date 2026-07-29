"""Прогон стратегий роутинга по набору кейсов task7.

Пишет по одной записи RouteOutcome на строку в raw/router_<стратегия>[_r<N>].jsonl.
Падение отдельного кейса не роняет прогон: кейс записывается с полем error, работа идёт дальше.

Запуск: python3 harness/run_router.py --dry-run --strategy all
        python3 harness/run_router.py --strategy route_conf --conf-threshold 0.75
        python3 harness/run_router.py --strategy all --repeats 3 --workers 3
"""

import argparse
import concurrent.futures
import dataclasses
import json
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import router
import router_spec

sys.path.insert(0, router_spec.TASK7_HARNESS_DIR)

import llm_client
import pipeline
import run_eval
import spec7


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Роутинг триажа ALVA между дешёвой локальной и сильной облачной моделью.",
    )
    parser.add_argument(
        "--strategy",
        choices=router_spec.STRATEGIES + (router_spec.STRATEGY_ALL,),
        default=router_spec.STRATEGY_ALL,
    )
    parser.add_argument(
        "--conf-threshold",
        dest="conf_threshold",
        type=float,
        default=router_spec.DEFAULT_CONFIDENCE_THRESHOLD,
    )
    parser.add_argument("--repeats", type=int, default=router_spec.DEFAULT_REPEATS)
    parser.add_argument("--cases", dest="cases_path", default=router_spec.CASES_PATH)
    parser.add_argument("--out-dir", dest="out_dir", default=router_spec.RAW_DIR)
    parser.add_argument("--workers", type=int, default=router_spec.DEFAULT_WORKERS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--cheap-model", dest="cheap_model", default=router_spec.CHEAP_MODEL)
    parser.add_argument("--cheap-base-url", dest="cheap_base_url", default=router_spec.CHEAP_BASE_URL)
    parser.add_argument("--cheap-adapters", dest="cheap_adapters", default=router_spec.CHEAP_ADAPTERS)
    parser.add_argument("--strong-model", dest="strong_model", default=router_spec.STRONG_MODEL)
    parser.add_argument(
        "--strong-base-url", dest="strong_base_url", default=router_spec.STRONG_BASE_URL
    )
    parser.add_argument("--strong-key-env", dest="strong_key_env", default=router_spec.STRONG_KEY_ENV)
    parser.add_argument("--timeout", type=int, default=spec7.REQUEST_TIMEOUT_SECONDS)
    return parser


def strategies_for(name: str) -> List[str]:
    if name == router_spec.STRATEGY_ALL:
        return list(router_spec.STRATEGIES)
    return [name]


def out_path_for(out_dir: str, strategy: str, repeat: int, repeats: int) -> str:
    name = router_spec.ROUTER_FILE_PREFIX + strategy
    if repeats > router_spec.MIN_REPEATS:
        name += router_spec.REPEAT_SUFFIX_PREFIX + str(repeat)
    return os.path.join(out_dir, name + router_spec.ROUTER_FILE_EXTENSION)


def uses_strong(strategy: str) -> bool:
    return strategy != router_spec.STRATEGY_ONLY_CHEAP


def risk_case_count(cases: List[Dict[str, Any]]) -> int:
    return sum(1 for case in cases if pipeline.detect_risk_markers(str(case.get("text", ""))))


def expected_calls(strategy: str, total: int, risk_count: int) -> Dict[str, Any]:
    if strategy == router_spec.STRATEGY_ONLY_CHEAP:
        return {"cheap": (total, total), "strong": (0, 0)}
    if strategy == router_spec.STRATEGY_ONLY_STRONG:
        return {"cheap": (0, 0), "strong": (total, total)}
    if strategy == router_spec.STRATEGY_ROUTE_RISK:
        stayed = total - risk_count
        return {"cheap": (stayed, stayed), "strong": (risk_count, risk_count)}
    if strategy == router_spec.STRATEGY_ROUTE_ALL:
        stayed = total - risk_count
        return {"cheap": (stayed, stayed), "strong": (risk_count, total)}
    return {"cheap": (total, total), "strong": (0, total)}


def format_range(bounds) -> str:
    low, high = bounds
    if low == high:
        return str(low)
    return "%d..%d" % (low, high)


def strong_call_cost(cases: List[Dict[str, Any]], model: str, calls: int) -> float:
    if not cases or not calls:
        return 0.0
    prompt_tokens = sum(
        run_eval.estimate_prompt_tokens(str(case.get("text", "")), spec7.TRIAGE_SYSTEM_PROMPT)
        for case in cases
    )
    average_prompt = prompt_tokens / len(cases)
    usage = {
        "prompt_tokens": int(average_prompt * calls),
        "completion_tokens": spec7.MAX_TOKENS * calls,
    }
    return llm_client.usage_cost(usage, model)


def print_dry_run(
    args: argparse.Namespace, cases: List[Dict[str, Any]], problem: Optional[str]
) -> None:
    sys.stdout.write("Сухой прогон роутера, сеть не трогается.\n\n")
    if problem is not None:
        sys.stdout.write("Кейсы прочитать не удалось: %s\n" % problem)
        return
    risk_count = risk_case_count(cases)
    location = llm_client.inference_location(args.strong_base_url)
    sys.stdout.write("Кейсов: %d, файл %s\n" % (len(cases), args.cases_path))
    sys.stdout.write("С признаком риска в тексте: %d\n" % risk_count)
    sys.stdout.write(
        "Дешёвый уровень: %s, %s, адаптер %s\n"
        % (args.cheap_model, args.cheap_base_url, args.cheap_adapters or "нет")
    )
    sys.stdout.write(
        "Сильный уровень: %s, %s, ключ %s\n"
        % (
            args.strong_model,
            args.strong_base_url,
            run_eval.describe_key_for(location, args.strong_key_env),
        )
    )
    sys.stdout.write("Порог уверенности для E_CONF: %.2f\n" % args.conf_threshold)
    sys.stdout.write("Повторов каждой стратегии: %d\n\n" % args.repeats)

    header = "%-14s %-38s %-12s %-12s %s" % (
        "стратегия",
        "что делает",
        "вызовов low",
        "вызовов high",
        "цена high, USD",
    )
    sys.stdout.write(header + "\n")
    sys.stdout.write("-" * len(header) + "\n")
    total_low = 0.0
    total_high = 0.0
    for strategy in strategies_for(args.strategy):
        calls = expected_calls(strategy, len(cases), risk_count)
        cost_low = strong_call_cost(cases, args.strong_model, calls["strong"][0]) * args.repeats
        cost_high = strong_call_cost(cases, args.strong_model, calls["strong"][1]) * args.repeats
        total_low += cost_low
        total_high += cost_high
        sys.stdout.write(
            "%-14s %-38s %-12s %-12s %s\n"
            % (
                strategy,
                router_spec.STRATEGY_TITLES[strategy],
                format_range(calls["cheap"]),
                format_range(calls["strong"]),
                "0" if cost_high == 0 else "%.4f..%.4f" % (cost_low, cost_high),
            )
        )
    sys.stdout.write(
        "\nИтого по всем прогонам, оценка сверху: %.4f USD (нижняя граница %.4f USD).\n"
        % (total_high, total_low)
    )
    sys.stdout.write(
        "Оценка грубая: выход считается по max_tokens %d, вход по %.1f символов на токен. "
        "Дешёвый уровень локальный, его вызовы стоят 0.\n"
        % (spec7.MAX_TOKENS, spec7.CHARS_PER_TOKEN_ESTIMATE)
    )
    sys.stdout.write(
        "Файлы прогонов: %s\n"
        % ", ".join(
            os.path.basename(out_path_for(args.out_dir, strategy, 1, args.repeats))
            for strategy in strategies_for(args.strategy)
        )
    )


def reasons_text(outcome: router.RouteOutcome) -> str:
    if not outcome.escalation_reasons:
        return "-"
    return ",".join(outcome.escalation_reasons)


def run_strategy(
    cases: List[Dict[str, Any]],
    policy: router.RoutePolicy,
    cheap_cfg: llm_client.ClientConfig,
    strong_cfg: llm_client.ClientConfig,
    out_path: str,
    workers: int,
) -> Dict[str, Any]:
    outcomes: Dict[int, router.RouteOutcome] = {}
    lock = threading.Lock()
    done = 0
    started = time.time()

    sys.stdout.write(
        "\nСтратегия %s: кейсов %d, потоков %d\n" % (policy.strategy, len(cases), workers)
    )
    sys.stdout.write("Вывод: %s\n" % out_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(
                router.route_one,
                str(case.get("text", "")),
                str(case.get("id")),
                policy,
                cheap_cfg,
                strong_cfg,
            ): position
            for position, case in enumerate(cases)
        }
        for future in concurrent.futures.as_completed(futures):
            position = futures[future]
            outcome = future.result()
            with lock:
                outcomes[position] = outcome
                done += 1
                sys.stdout.write(
                    "  [%d/%d] %-14s %-12s %-7s low %d high %d, %d мс, причины %s%s\n"
                    % (
                        done,
                        len(cases),
                        outcome.case_id,
                        outcome.final_route or router_spec.NO_ROUTE,
                        outcome.final_status,
                        outcome.calls_cheap,
                        outcome.calls_strong,
                        outcome.latency_ms,
                        reasons_text(outcome),
                        ("  ошибка: " + outcome.error[:60]) if outcome.error else "",
                    )
                )
                sys.stdout.flush()

    ordered = [outcomes[position] for position in sorted(outcomes)]
    with open(out_path, "w", encoding="utf-8") as handle:
        for outcome in ordered:
            handle.write(json.dumps(dataclasses.asdict(outcome), ensure_ascii=False) + "\n")

    escalated = sum(1 for outcome in ordered if outcome.escalated)
    failed = sum(1 for outcome in ordered if outcome.error)
    cost = sum(outcome.cost_usd for outcome in ordered)
    calls_cheap = sum(outcome.calls_cheap for outcome in ordered)
    calls_strong = sum(outcome.calls_strong for outcome in ordered)
    elapsed = time.time() - started
    sys.stdout.write(
        "Стратегия %s готова: эскалировано %d из %d, вызовов low %d, high %d, "
        "стоимость %.6f USD, с ошибкой %d, время %.1f с\n"
        % (
            policy.strategy,
            escalated,
            len(ordered),
            calls_cheap,
            calls_strong,
            cost,
            failed,
            elapsed,
        )
    )
    return {
        "strategy": policy.strategy,
        "cases": len(ordered),
        "escalated": escalated,
        "failed": failed,
        "cost_usd": cost,
        "out_path": out_path,
    }


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.workers <= 0:
        sys.stderr.write("Значение --workers должно быть больше нуля.\n")
        return router_spec.EXIT_CONFIG_ERROR
    if args.repeats < router_spec.MIN_REPEATS:
        sys.stderr.write("Значение --repeats должно быть не меньше %d.\n" % router_spec.MIN_REPEATS)
        return router_spec.EXIT_CONFIG_ERROR
    if args.limit < 0:
        sys.stderr.write("Значение --limit не может быть отрицательным.\n")
        return router_spec.EXIT_CONFIG_ERROR
    if not 0.0 <= args.conf_threshold <= 1.0:
        sys.stderr.write("Значение --conf-threshold должно лежать от 0.0 до 1.0.\n")
        return router_spec.EXIT_CONFIG_ERROR

    cases: List[Dict[str, Any]] = []
    cases_problem: Optional[str] = None
    try:
        cases = run_eval.load_cases(args.cases_path, args.limit)
    except run_eval.CasesError as cases_error:
        cases_problem = str(cases_error)
    except OSError as os_error:
        cases_problem = "не читается %s: %s" % (args.cases_path, os_error)

    if args.dry_run:
        print_dry_run(args, cases, cases_problem)
        return router_spec.EXIT_OK

    if cases_problem is not None:
        sys.stderr.write("Не могу прочитать кейсы: %s\n" % cases_problem)
        return router_spec.EXIT_DATA_ERROR

    selected = strategies_for(args.strategy)
    needs_strong = any(uses_strong(strategy) for strategy in selected)
    strong_location = llm_client.inference_location(args.strong_base_url)
    if needs_strong and strong_location == spec7.LOCATION_CLOUD:
        if not llm_client.read_api_key(args.strong_key_env):
            sys.stderr.write(
                "Ключ %s не найден ни в окружении, ни в %s. "
                "Экспортируйте переменную окружения и повторите: export %s=<ваш ключ>\n"
                % (args.strong_key_env, spec7.LOCAL_PROPERTIES_PATH, args.strong_key_env)
            )
            return router_spec.EXIT_CONFIG_ERROR

    if args.cheap_adapters and not os.path.isdir(args.cheap_adapters):
        sys.stderr.write(
            "ВНИМАНИЕ: каталог адаптера %s не найден. Если сервер запущен здесь же, "
            "запрос уйдёт с несуществующим путём и модель ответит без адаптера.\n"
            % args.cheap_adapters
        )

    if not os.path.isdir(args.out_dir):
        os.makedirs(args.out_dir)

    cheap_cfg = router.cheap_config(
        args.cheap_model, args.cheap_base_url, args.cheap_adapters, args.timeout
    )
    strong_cfg = router.strong_config(
        args.strong_model, args.strong_base_url, args.strong_key_env, args.timeout
    )

    sys.stdout.write(
        "Дешёвый уровень: %s, %s, адаптер %s\n"
        % (cheap_cfg.model, cheap_cfg.location, cheap_cfg.adapter or "нет")
    )
    sys.stdout.write(
        "Сильный уровень: %s, %s, ключ %s\n"
        % (
            strong_cfg.model,
            strong_cfg.location,
            run_eval.describe_key_for(strong_cfg.location, args.strong_key_env),
        )
    )
    sys.stdout.write("Порог уверенности для E_CONF: %.2f\n" % args.conf_threshold)
    sys.stdout.write(
        "Стратегий: %d, повторов каждой: %d\n" % (len(selected), args.repeats)
    )

    summaries: List[Dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for strategy in selected:
            policy = router.policy_for(strategy, args.conf_threshold)
            out_path = out_path_for(args.out_dir, strategy, repeat, args.repeats)
            summaries.append(
                run_strategy(cases, policy, cheap_cfg, strong_cfg, out_path, args.workers)
            )

    total_failed = sum(summary["failed"] for summary in summaries)
    total_cost = sum(summary["cost_usd"] for summary in summaries)
    sys.stdout.write(
        "\nГотово. Прогонов %d, кейсов с ошибкой суммарно %d, потрачено %.6f USD\n"
        % (len(summaries), total_failed, total_cost)
    )
    return router_spec.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
