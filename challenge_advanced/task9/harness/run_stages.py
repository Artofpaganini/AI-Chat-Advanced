"""Прогон двух вариантов инференса по набору кейсов task7.

Пишет по одной записи на кейс в raw/monolithic_runs.jsonl и raw/multistage_runs.jsonl.
Падение отдельного кейса не роняет прогон: кейс записывается с полем error, работа идёт дальше.

Модели задаются двумя способами. Общий - --model, --base-url, --key-env, --adapters: тогда
монолит и все три этапа работают на одной модели, как требует SPEC раздел 5. Поэтапный -
--stage1-model и родня: это отдельный эксперимент поверх, для него сравнение с монолитом
честным уже не будет, о чём скрипт предупреждает.

Запуск: python3 harness/run_stages.py --dry-run --mode both
        python3 harness/run_stages.py --mode multistage --limit 3 --workers 2
        python3 harness/run_stages.py --mode both --repeats 3 --workers 4
"""

import argparse
import concurrent.futures
import dataclasses
import json
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import stages
import stages_spec

sys.path.insert(0, stages_spec.TASK7_HARNESS_DIR)

import llm_client
import run_eval
import spec7

FACTS_ESTIMATE_CHARS = 160
DECISION_ESTIMATE_CHARS = 80
STAGE_ARGUMENT_NAMES = {
    stages_spec.STAGE_PARSE: "stage1",
    stages_spec.STAGE_DECIDE: "stage2",
    stages_spec.STAGE_ANSWER: "stage3",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Монолитный и трёхэтапный инференс триажа ALVA на одном наборе кейсов.",
    )
    parser.add_argument(
        "--mode",
        choices=(stages_spec.MODE_MONOLITHIC, stages_spec.MODE_MULTISTAGE, stages_spec.MODE_BOTH),
        default=stages_spec.MODE_BOTH,
    )
    parser.add_argument(
        "--cases", dest="cases_paths", nargs="*", default=[stages_spec.CASES_PATH]
    )
    parser.add_argument("--out-dir", dest="out_dir", default=stages_spec.RAW_DIR)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=stages_spec.DEFAULT_WORKERS)
    parser.add_argument("--repeats", type=int, default=stages_spec.DEFAULT_REPEATS)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--model", default=stages_spec.DEFAULT_MODEL)
    parser.add_argument("--base-url", dest="base_url", default=stages_spec.DEFAULT_BASE_URL)
    parser.add_argument("--key-env", dest="key_env", default=stages_spec.DEFAULT_KEY_ENV)
    parser.add_argument("--adapters", dest="adapters", default="")
    for stage, prefix in STAGE_ARGUMENT_NAMES.items():
        parser.add_argument("--%s-model" % prefix, dest="%s_model" % prefix, default="")
        parser.add_argument("--%s-base-url" % prefix, dest="%s_base_url" % prefix, default="")
        parser.add_argument("--%s-key-env" % prefix, dest="%s_key_env" % prefix, default="")
    parser.add_argument("--timeout", type=int, default=spec7.REQUEST_TIMEOUT_SECONDS)
    parser.add_argument("--thinking", dest="thinking", action="store_true")
    return parser


def modes_for(name: str) -> List[str]:
    if name == stages_spec.MODE_BOTH:
        return list(stages_spec.MODES)
    return [name]


def out_path_for(out_dir: str, mode: str, repeat: int, repeats: int) -> str:
    name = mode + stages_spec.RUNS_FILE_SUFFIX
    if repeats > stages_spec.MIN_REPEATS:
        name += stages_spec.REPEAT_SUFFIX_PREFIX + str(repeat)
    return os.path.join(out_dir, name + stages_spec.RUNS_FILE_EXTENSION)


def endpoint_for(args: argparse.Namespace, stage: str) -> Dict[str, str]:
    prefix = STAGE_ARGUMENT_NAMES.get(stage, "")
    model = getattr(args, "%s_model" % prefix, "") or args.model
    base_url = getattr(args, "%s_base_url" % prefix, "") or args.base_url
    key_env = getattr(args, "%s_key_env" % prefix, "") or args.key_env
    same_target = model == args.model and base_url == args.base_url and key_env == args.key_env
    return {
        "model": model,
        "base_url": base_url,
        "key_env": key_env,
        "adapters": args.adapters if same_target else "",
    }


def stages_are_split(args: argparse.Namespace) -> bool:
    endpoints = [endpoint_for(args, stage) for stage in stages_spec.MULTISTAGE_STAGES]
    return any(
        endpoint["model"] != args.model or endpoint["base_url"] != args.base_url
        for endpoint in endpoints
    )


# chat_template_kwargs из run_eval.build_extra_payload рассчитан на локальный vLLM. Прямые имена
# облачных моделей deepseek-v4-flash и deepseek-v4-pro (в отличие от алиаса deepseek-chat) по
# умолчанию думают вслух и не слушают этот параметр - весь потолок токенов уходит в reasoning_content,
# а content приходит пустым. Проверено живым запросом. reasoning_effort=none их выключает, deepseek-chat
# этот параметр просто игнорирует.
CLOUD_REASONING_OFF = {"reasoning_effort": "none"}


def build_extra_payload(endpoint: Dict[str, str], thinking_off: bool, location: str) -> Optional[Dict[str, Any]]:
    payload = run_eval.build_extra_payload(thinking_off, endpoint["adapters"]) or {}
    if thinking_off and location == spec7.LOCATION_CLOUD:
        payload = dict(payload)
        payload.update(CLOUD_REASONING_OFF)
    return payload or None


def build_config(
    endpoint: Dict[str, str], timeout: int, thinking_off: bool
) -> Tuple[Optional[llm_client.ClientConfig], Optional[str]]:
    location = llm_client.inference_location(endpoint["base_url"])
    api_key = ""
    if location == spec7.LOCATION_CLOUD:
        api_key = llm_client.read_api_key(endpoint["key_env"])
        if not api_key:
            return None, (
                "Ключ %s не найден ни в окружении, ни в %s. "
                "Экспортируйте переменную окружения и повторите: export %s=<ваш ключ>"
                % (endpoint["key_env"], spec7.LOCAL_PROPERTIES_PATH, endpoint["key_env"])
            )
    return (
        llm_client.ClientConfig(
            model=endpoint["model"],
            base_url=endpoint["base_url"],
            api_key=api_key,
            timeout=timeout,
            extra_payload=build_extra_payload(endpoint, thinking_off, location),
        ),
        None,
    )


def stage_prompt_chars(stage: str, case_text: str) -> Tuple[int, int]:
    if stage == stages_spec.STAGE_MONOLITHIC:
        return len(stages_spec.MONOLITHIC_SYSTEM_PROMPT), len(case_text)
    if stage == stages_spec.STAGE_PARSE:
        return len(stages_spec.STAGE1_SYSTEM_PROMPT) + len(stages_spec.STAGE1_USER_TEMPLATE), len(
            case_text
        )
    if stage == stages_spec.STAGE_DECIDE:
        return (
            len(stages_spec.STAGE2_SYSTEM_PROMPT) + len(stages_spec.STAGE2_USER_TEMPLATE),
            FACTS_ESTIMATE_CHARS,
        )
    return (
        len(stages_spec.STAGE3_SYSTEM_PROMPT) + len(stages_spec.STAGE3_USER_TEMPLATE),
        FACTS_ESTIMATE_CHARS + DECISION_ESTIMATE_CHARS,
    )


def stage_cost_estimate(stage: str, cases: List[Dict[str, Any]], model: str, base_url: str) -> float:
    if not cases:
        return 0.0
    if llm_client.inference_location(base_url) == spec7.LOCATION_LOCAL:
        return 0.0
    prompt_tokens = 0
    for case in cases:
        system_chars, user_chars = stage_prompt_chars(stage, str(case.get("text", "")))
        prompt_tokens += int((system_chars + user_chars) / spec7.CHARS_PER_TOKEN_ESTIMATE) + 1
    usage = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": stages_spec.STAGE_MAX_TOKENS[stage] * len(cases),
    }
    return llm_client.usage_cost(usage, model)


def mode_stages(mode: str) -> Tuple[str, ...]:
    if mode == stages_spec.MODE_MONOLITHIC:
        return (stages_spec.STAGE_MONOLITHIC,)
    return stages_spec.MULTISTAGE_STAGES


def print_dry_run(
    args: argparse.Namespace, cases: List[Dict[str, Any]], problem: Optional[str]
) -> None:
    sys.stdout.write("Сухой прогон декомпозиции, сеть не трогается.\n\n")
    if problem is not None:
        sys.stdout.write("Кейсы прочитать не удалось: %s\n" % problem)
        return
    sys.stdout.write("Кейсов: %d, файлы %s\n" % (len(cases), ", ".join(args.cases_paths)))
    sys.stdout.write("Повторов каждого варианта: %d\n" % args.repeats)
    sys.stdout.write(
        "Монолит: %s, %s, ключ %s\n"
        % (
            args.model,
            args.base_url,
            run_eval.describe_key_for(llm_client.inference_location(args.base_url), args.key_env),
        )
    )
    for stage in stages_spec.MULTISTAGE_STAGES:
        endpoint = endpoint_for(args, stage)
        sys.stdout.write(
            "%s: %s, %s, потолок ответа %d токенов\n"
            % (
                stages_spec.STAGE_TITLES[stage],
                endpoint["model"],
                endpoint["base_url"],
                stages_spec.STAGE_MAX_TOKENS[stage],
            )
        )
    if stages_are_split(args):
        sys.stdout.write(
            "ВНИМАНИЕ: этапы работают на разных моделях. По SPEC раздел 5 это отдельный "
            "эксперимент, сравнивать такой прогон с монолитом как равный нельзя.\n"
        )
    sys.stdout.write("\n")

    header = "%-12s %-24s %-10s %-14s %s" % (
        "вариант",
        "этап",
        "вызовов",
        "потолок токенов",
        "оценка цены, USD",
    )
    sys.stdout.write(header + "\n")
    sys.stdout.write("-" * len(header) + "\n")
    grand_total = 0.0
    for mode in modes_for(args.mode):
        mode_total = 0.0
        mode_calls = 0
        for stage in mode_stages(mode):
            endpoint = (
                {"model": args.model, "base_url": args.base_url}
                if stage == stages_spec.STAGE_MONOLITHIC
                else endpoint_for(args, stage)
            )
            cost = (
                stage_cost_estimate(stage, cases, endpoint["model"], endpoint["base_url"])
                * args.repeats
            )
            mode_total += cost
            mode_calls += len(cases) * args.repeats
            sys.stdout.write(
                "%-12s %-24s %-10d %-14d %.4f\n"
                % (
                    mode,
                    stages_spec.STAGE_TITLES[stage],
                    len(cases) * args.repeats,
                    stages_spec.STAGE_MAX_TOKENS[stage],
                    cost,
                )
            )
        grand_total += mode_total
        sys.stdout.write(
            "%-12s %-24s %-10d %-14s %.4f\n"
            % (mode, "итого по варианту", mode_calls, stages_spec.NOT_AVAILABLE, mode_total)
        )
    sys.stdout.write("\nИтого оценка сверху: %.4f USD\n" % grand_total)
    sys.stdout.write(
        "Оценка грубая: выход считается по потолку токенов этапа, вход по %.1f символов на токен, "
        "факты для этапов 2 и 3 приняты за %d символов. Локальные вызовы стоят 0.\n"
        % (spec7.CHARS_PER_TOKEN_ESTIMATE, FACTS_ESTIMATE_CHARS)
    )
    sys.stdout.write(
        "Файлы прогонов: %s\n"
        % ", ".join(
            os.path.basename(out_path_for(args.out_dir, mode, 1, args.repeats))
            for mode in modes_for(args.mode)
        )
    )


def run_case(
    mode: str,
    case: Dict[str, Any],
    configs: Dict[str, llm_client.ClientConfig],
) -> stages.MultiStageDecision:
    case_text = str(case.get("text", ""))
    case_id = str(case.get("id"))
    if mode == stages_spec.MODE_MONOLITHIC:
        return stages.run_monolithic(case_text, configs[stages_spec.STAGE_MONOLITHIC], case_id)
    return stages.run_multistage(
        case_text,
        configs[stages_spec.STAGE_PARSE],
        configs[stages_spec.STAGE_DECIDE],
        configs[stages_spec.STAGE_ANSWER],
        case_id,
    )


def stage_marks(decision: stages.MultiStageDecision) -> str:
    if not decision.stages:
        return stages_spec.NOT_AVAILABLE
    return "".join("+" if stage.ok else "x" for stage in decision.stages)


def violations_text(decision: stages.MultiStageDecision) -> str:
    codes: List[str] = []
    for stage in decision.stages:
        for code in stage.violations:
            if code not in codes:
                codes.append(code)
    if not codes:
        return "-"
    return ",".join(codes)


def run_mode(
    cases: List[Dict[str, Any]],
    mode: str,
    configs: Dict[str, llm_client.ClientConfig],
    out_path: str,
    workers: int,
) -> Dict[str, Any]:
    results: Dict[int, stages.MultiStageDecision] = {}
    lock = threading.Lock()
    done = 0
    started = time.time()

    sys.stdout.write("\nВариант %s: кейсов %d, потоков %d\n" % (mode, len(cases), workers))
    sys.stdout.write("Вывод: %s\n" % out_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(run_case, mode, case, configs): position
            for position, case in enumerate(cases)
        }
        for future in concurrent.futures.as_completed(futures):
            position = futures[future]
            decision = future.result()
            with lock:
                results[position] = decision
                done += 1
                sys.stdout.write(
                    "  [%d/%d] %-14s %-12s этапы %-4s наруш %-22s %5d мс  %.6f USD%s\n"
                    % (
                        done,
                        len(cases),
                        decision.case_id,
                        decision.route or stages_spec.NO_ROUTE,
                        stage_marks(decision),
                        violations_text(decision),
                        decision.total_latency_ms,
                        decision.total_cost_usd,
                        ("  ошибка: " + decision.error[:60]) if decision.error else "",
                    )
                )
                sys.stdout.flush()

    ordered = [results[position] for position in sorted(results)]
    with open(out_path, "w", encoding="utf-8") as handle:
        for decision in ordered:
            handle.write(json.dumps(dataclasses.asdict(decision), ensure_ascii=False) + "\n")

    failed = sum(1 for decision in ordered if decision.failed_stage is not None)
    errors = sum(1 for decision in ordered if decision.error)
    cost = sum(decision.total_cost_usd for decision in ordered)
    calls = sum(decision.calls for decision in ordered)
    elapsed = time.time() - started
    sys.stdout.write(
        "Вариант %s готов: кейсов %d, вызовов %d, со сбоем этапа %d, с ошибкой %d, "
        "стоимость %.6f USD, время %.1f с\n"
        % (mode, len(ordered), calls, failed, errors, cost, elapsed)
    )
    return {
        "mode": mode,
        "cases": len(ordered),
        "calls": calls,
        "failed": failed,
        "errors": errors,
        "cost_usd": cost,
        "out_path": out_path,
    }


def build_configs(
    args: argparse.Namespace, selected: List[str]
) -> Tuple[Dict[str, llm_client.ClientConfig], Optional[str]]:
    thinking_off = not args.thinking
    configs: Dict[str, llm_client.ClientConfig] = {}
    needed: List[Tuple[str, Dict[str, str]]] = []
    if stages_spec.MODE_MONOLITHIC in selected:
        needed.append(
            (
                stages_spec.STAGE_MONOLITHIC,
                {
                    "model": args.model,
                    "base_url": args.base_url,
                    "key_env": args.key_env,
                    "adapters": args.adapters,
                },
            )
        )
    if stages_spec.MODE_MULTISTAGE in selected:
        for stage in stages_spec.MULTISTAGE_STAGES:
            needed.append((stage, endpoint_for(args, stage)))
    for stage, endpoint in needed:
        config, problem = build_config(endpoint, args.timeout, thinking_off)
        if problem is not None:
            return {}, problem
        configs[stage] = config
    return configs, None


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.workers <= 0:
        sys.stderr.write("Значение --workers должно быть больше нуля.\n")
        return stages_spec.EXIT_CONFIG_ERROR
    if args.limit < 0:
        sys.stderr.write("Значение --limit не может быть отрицательным.\n")
        return stages_spec.EXIT_CONFIG_ERROR
    if args.repeats < stages_spec.MIN_REPEATS:
        sys.stderr.write(
            "Значение --repeats должно быть не меньше %d.\n" % stages_spec.MIN_REPEATS
        )
        return stages_spec.EXIT_CONFIG_ERROR

    cases: List[Dict[str, Any]] = []
    cases_problem: Optional[str] = None
    try:
        for path in args.cases_paths:
            cases.extend(run_eval.load_cases(path, 0))
        if args.limit:
            cases = cases[: args.limit]
    except run_eval.CasesError as cases_error:
        cases_problem = str(cases_error)
    except OSError as os_error:
        cases_problem = "не читается %s: %s" % (", ".join(args.cases_paths), os_error)

    if args.dry_run:
        print_dry_run(args, cases, cases_problem)
        return stages_spec.EXIT_OK

    if cases_problem is not None:
        sys.stderr.write("Не могу прочитать кейсы: %s\n" % cases_problem)
        return stages_spec.EXIT_DATA_ERROR

    selected = modes_for(args.mode)
    configs, config_problem = build_configs(args, selected)
    if config_problem is not None:
        sys.stderr.write(config_problem + "\n")
        return stages_spec.EXIT_CONFIG_ERROR

    if args.adapters and not os.path.isdir(args.adapters):
        sys.stderr.write(
            "ВНИМАНИЕ: каталог адаптера %s не найден. Если сервер запущен здесь же, "
            "запрос уйдёт с несуществующим путём и модель ответит без адаптера.\n" % args.adapters
        )

    if not os.path.isdir(args.out_dir):
        os.makedirs(args.out_dir)

    for stage, config in sorted(configs.items()):
        sys.stdout.write(
            "%s: %s, %s, адаптер %s\n"
            % (
                stages_spec.STAGE_TITLES[stage],
                config.model,
                config.location,
                config.adapter or "нет",
            )
        )
    if stages_spec.MODE_MULTISTAGE in selected and stages_are_split(args):
        sys.stdout.write(
            "ВНИМАНИЕ: этапы работают на разных моделях, это отдельный эксперимент поверх SPEC.\n"
        )
    sys.stdout.write("Вариантов: %d, повторов каждого: %d\n" % (len(selected), args.repeats))

    summaries: List[Dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for mode in selected:
            out_path = out_path_for(args.out_dir, mode, repeat, args.repeats)
            summaries.append(run_mode(cases, mode, configs, out_path, args.workers))

    total_cost = sum(summary["cost_usd"] for summary in summaries)
    total_errors = sum(summary["errors"] for summary in summaries)
    sys.stdout.write(
        "\nГотово. Прогонов %d, кейсов с ошибкой суммарно %d, потрачено %.6f USD\n"
        % (len(summaries), total_errors, total_cost)
    )
    return stages_spec.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
