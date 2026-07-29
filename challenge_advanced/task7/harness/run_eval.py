"""Прогон набора кейсов в двух режимах: baseline и pipeline.

Пишет по одной записи Decision на строку в raw/baseline_runs.jsonl и raw/pipeline_runs.jsonl.
Падение отдельного кейса не роняет прогон: кейс записывается с полем error, работа продолжается.

Критик может судить другой моделью: флаги --critic-model, --critic-base-url, --critic-key-env.
Если их не задать, критик работает на модели основного прохода - поведение не меняется.
Деньги считаются раздельно: каждая модель по своей цене.

Дообученную модель меряем через флаг --adapters: путь к каталогу LoRA уходит полем adapters
в теле каждого запроса. Флаг --adapter-path у mlx_lm.server молча игнорируется, поэтому только так.
У критика свой флаг --critic-adapters.

Запуск: python3 harness/run_eval.py --dry-run
        python3 harness/run_eval.py --mode both --workers 4
        python3 harness/run_eval.py --mode pipeline --base-url http://127.0.0.1:8080/v1 \\
            --model mlx-community/Qwen3-1.7B-4bit --adapters ~/models/alva-triage-qwen-lora
        python3 harness/run_eval.py --mode pipeline --self-check-trigger risk
        python3 harness/run_eval.py --mode pipeline --model gpt-4o-mini \\
            --base-url https://api.openai.com/v1 --key-env OPENAI_API_KEY \\
            --critic-model deepseek-chat --critic-base-url https://api.deepseek.com/v1 \\
            --critic-key-env DEEPSEEK_API_KEY
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

import guards
import llm_client
import pipeline
import spec7

DEFAULT_WORKERS = 4
EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2
MODE_BOTH = "both"
SELF_CHECK_SHARE_ESTIMATE = 0.5
REPAIR_SHARE_ESTIMATE = 0.2
PROGRESS_PREVIEW_CHARS = 40
CRITIC_PROMPT_TEXT = spec7.CRITIC_SYSTEM_PROMPT + spec7.CRITIC_USER_TEMPLATE


class CasesError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Прогон триажа ALVA: baseline против полного цикла с оценкой уверенности.",
    )
    parser.add_argument("--cases", dest="cases_path", default=spec7.DEFAULT_CASES_PATH)
    parser.add_argument(
        "--mode",
        choices=(spec7.MODE_BASELINE, spec7.MODE_PIPELINE, MODE_BOTH),
        default=MODE_BOTH,
    )
    parser.add_argument("--out-dir", dest="out_dir", default=spec7.RAW_DIR)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--model", default=spec7.DEFAULT_MODEL)
    parser.add_argument("--base-url", dest="base_url", default=spec7.DEFAULT_BASE_URL)
    parser.add_argument("--key-env", dest="key_env", default=spec7.DEFAULT_KEY_ENV)
    parser.add_argument("--adapters", dest="adapters", default="")
    parser.add_argument("--critic-model", dest="critic_model", default="")
    parser.add_argument("--critic-base-url", dest="critic_base_url", default="")
    parser.add_argument("--critic-key-env", dest="critic_key_env", default="")
    parser.add_argument("--critic-adapters", dest="critic_adapters", default="")
    parser.add_argument("--out-suffix", dest="out_suffix", default="")
    parser.add_argument("--timeout", type=int, default=spec7.REQUEST_TIMEOUT_SECONDS)
    parser.add_argument("--thinking", dest="thinking", action="store_true")
    parser.add_argument(
        "--self-check-trigger",
        dest="self_check_trigger",
        choices=spec7.SELF_CHECK_TRIGGERS,
        default=spec7.SELF_CHECK_TRIGGER_AGREEMENT,
    )
    parser.add_argument(
        "--always-self-check", dest="always_self_check", action="store_true"
    )
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    return parser


def critic_endpoint(args: argparse.Namespace) -> Dict[str, str]:
    model = args.critic_model or args.model
    base_url = args.critic_base_url or args.base_url
    key_env = args.critic_key_env or args.key_env
    same_target = model == args.model and base_url == args.base_url and key_env == args.key_env
    adapters = args.critic_adapters
    if not adapters and same_target:
        adapters = args.adapters
    return {
        "model": model,
        "base_url": base_url,
        "key_env": key_env,
        "adapters": adapters,
    }


def critic_is_separate(args: argparse.Namespace) -> bool:
    endpoint = critic_endpoint(args)
    return (
        endpoint["model"] != args.model
        or endpoint["base_url"] != args.base_url
        or endpoint["key_env"] != args.key_env
        or endpoint["adapters"] != args.adapters
    )


def describe_adapter(path: str) -> str:
    if not path:
        return "не применяется, работает базовая модель"
    return "%s - уходит полем %s в теле каждого запроса" % (path, spec7.ADAPTERS_PAYLOAD_KEY)


def describe_critic_endpoint(args: argparse.Namespace) -> str:
    endpoint = critic_endpoint(args)
    if not critic_is_separate(args):
        return "%s - та же модель, что и основной проход" % endpoint["model"]
    return "%s - отдельная модель, независимая от основного прохода" % endpoint["model"]


def warn_shared_key_env(args: argparse.Namespace) -> None:
    endpoint = critic_endpoint(args)
    if endpoint["base_url"] == args.base_url or endpoint["key_env"] != args.key_env:
        return
    sys.stderr.write(
        "ВНИМАНИЕ: критик смотрит на другой адрес (%s), но ключ берётся из той же переменной %s, "
        "что и у основной модели. Если это разные провайдеры, укажите --critic-key-env.\n"
        % (endpoint["base_url"], endpoint["key_env"])
    )


def build_extra_payload(thinking_off: bool, adapters: str) -> Optional[Dict[str, Any]]:
    payload: Dict[str, Any] = {}
    if thinking_off:
        payload.update(spec7.NO_THINKING_PAYLOAD)
    if adapters:
        payload[spec7.ADAPTERS_PAYLOAD_KEY] = adapters
    if not payload:
        return None
    return payload


def warn_missing_adapter(title: str, path: str) -> None:
    if not path or os.path.isdir(path):
        return
    sys.stderr.write(
        "ВНИМАНИЕ: каталог адаптера %s (%s) не найден на этой машине. "
        "Если сервер запущен здесь же, запрос уйдёт с несуществующим путём и модель ответит без адаптера.\n"
        % (title, path)
    )


def build_critic_config(
    args: argparse.Namespace,
) -> Tuple[Optional[llm_client.ClientConfig], Optional[str]]:
    if not critic_is_separate(args):
        return None, None
    endpoint = critic_endpoint(args)
    location = llm_client.inference_location(endpoint["base_url"])
    api_key = "" if location == spec7.LOCATION_LOCAL else llm_client.read_api_key(endpoint["key_env"])
    if location == spec7.LOCATION_CLOUD and not api_key:
        return None, (
            "Ключ критика %s не найден ни в окружении, ни в %s. "
            "Экспортируйте переменную окружения и повторите: export %s=<ваш ключ>"
            % (endpoint["key_env"], spec7.LOCAL_PROPERTIES_PATH, endpoint["key_env"])
        )
    thinking_off = location == spec7.LOCATION_LOCAL and not args.thinking
    config = llm_client.ClientConfig(
        model=endpoint["model"],
        base_url=endpoint["base_url"],
        api_key=api_key,
        timeout=args.timeout,
        extra_payload=build_extra_payload(thinking_off, endpoint["adapters"]),
    )
    return config, None


def resolve_trigger(args: argparse.Namespace) -> str:
    if not args.always_self_check:
        return args.self_check_trigger
    if args.self_check_trigger != spec7.SELF_CHECK_TRIGGER_AGREEMENT:
        sys.stderr.write(
            "ВНИМАНИЕ: --always-self-check это синоним --self-check-trigger always, "
            "он перебил указанный режим %s.\n" % args.self_check_trigger
        )
    return spec7.SELF_CHECK_TRIGGER_ALWAYS


def load_cases(path: str, limit: int) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        raise CasesError(
            "файл кейсов не найден: %s. Его собирает отдельный шаг подготовки данных - "
            "положите cases.jsonl в data/ и повторите." % path
        )
    cases: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except ValueError as parse_error:
                raise CasesError(
                    "строка %d в %s не парсится как JSON: %s" % (line_number, path, parse_error)
                )
            if not isinstance(payload, dict):
                raise CasesError("строка %d в %s не объект JSON" % (line_number, path))
            case_id = payload.get("id")
            if not isinstance(case_id, str) or not case_id:
                raise CasesError("строка %d в %s без строкового поля id" % (line_number, path))
            if "text" not in payload:
                raise CasesError("кейс %s в %s без поля text" % (case_id, path))
            cases.append(payload)
            if limit and len(cases) >= limit:
                break
    if not cases:
        raise CasesError("файл кейсов пустой: %s" % path)
    return cases


def modes_for(mode: str) -> List[str]:
    if mode == MODE_BOTH:
        return [spec7.MODE_BASELINE, spec7.MODE_PIPELINE]
    return [mode]


def out_path_for(out_dir: str, mode: str, suffix: str = "") -> str:
    name = spec7.BASELINE_RUNS_NAME if mode == spec7.MODE_BASELINE else spec7.PIPELINE_RUNS_NAME
    if suffix:
        stem, extension = os.path.splitext(name)
        name = stem + suffix + extension
    return os.path.join(out_dir, name)


def estimate_prompt_tokens(case_text: str, system_prompt: str) -> int:
    total_chars = len(case_text) + len(system_prompt)
    return int(total_chars / spec7.CHARS_PER_TOKEN_ESTIMATE) + 1


def markers_of(case: Dict[str, Any]) -> List[str]:
    return pipeline.detect_risk_markers(str(case.get("text", "")))


def risk_share(cases: List[Dict[str, Any]]) -> float:
    if not cases:
        return 0.0
    with_markers = sum(1 for case in cases if markers_of(case))
    return round(with_markers / len(cases), 4)


def risk_by_group(cases: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    breakdown: Dict[str, List[int]] = {}
    for case in cases:
        group = str(case.get("group", "-"))
        bucket = breakdown.setdefault(group, [0, 0])
        bucket[1] += 1
        if markers_of(case):
            bucket[0] += 1
    return breakdown


def risk_by_label(cases: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for case in cases:
        for label in markers_of(case):
            counts[label] = counts.get(label, 0) + 1
    return counts


def self_check_share_for(trigger: str, cases: List[Dict[str, Any]]) -> float:
    if trigger == spec7.SELF_CHECK_TRIGGER_ALWAYS:
        return 1.0
    if trigger == spec7.SELF_CHECK_TRIGGER_RISK:
        return risk_share(cases)
    return SELF_CHECK_SHARE_ESTIMATE


def describe_self_check_share(trigger: str, share: float) -> str:
    if trigger == spec7.SELF_CHECK_TRIGGER_ALWAYS:
        return "Доля self-check: 100%, критик зовётся на каждом кейсе, считать нечего."
    if trigger == spec7.SELF_CHECK_TRIGGER_RISK:
        return (
            "Доля self-check: %.0f%%, посчитана по самим кейсам через detect_risk_markers. "
            "Это оценка снизу: старое условие по разбросу голосов добавит сверху те кейсы, "
            "где признака риска в тексте нет, а голоса разошлись."
            % (share * 100)
        )
    return (
        "Доля self-check: взята как %.0f%% - при триггере agreement её нельзя посчитать заранее, "
        "она зависит от разброса голосов, который виден только в живом прогоне."
        % (share * 100)
    )


def endpoint_of(model: str, base_url: str) -> Dict[str, str]:
    return {
        "model": model,
        "base_url": base_url,
        "location": llm_client.inference_location(base_url),
    }


def main_endpoint(args: argparse.Namespace) -> Dict[str, str]:
    return endpoint_of(args.model, args.base_url)


def critic_endpoint_of(args: argparse.Namespace) -> Dict[str, str]:
    endpoint = critic_endpoint(args)
    return endpoint_of(endpoint["model"], endpoint["base_url"])


def max_tokens_for(location: str) -> int:
    if location == spec7.LOCATION_LOCAL:
        return spec7.LOCAL_MAX_TOKENS
    return spec7.MAX_TOKENS


def estimated_cost(
    prompt_tokens: float, completion_tokens: float, endpoint: Dict[str, str]
) -> float:
    if endpoint["location"] == spec7.LOCATION_LOCAL:
        return 0.0
    return llm_client.usage_cost(
        {"prompt_tokens": int(prompt_tokens), "completion_tokens": int(completion_tokens)},
        endpoint["model"],
    )


def estimate_mode(
    cases: List[Dict[str, Any]],
    mode: str,
    main: Dict[str, str],
    critic: Dict[str, str],
    trigger: str = spec7.SELF_CHECK_TRIGGER_AGREEMENT,
) -> Dict[str, Any]:
    if mode == spec7.MODE_BASELINE:
        main_calls_per_case = 1.0
        billable = cases
        self_check_share = 0.0
    else:
        billable = [case for case in cases if guards.check_input(str(case.get("text", ""))).ok]
        self_check_share = self_check_share_for(trigger, billable)
        main_calls_per_case = spec7.REDUNDANCY_SAMPLES * (1.0 + REPAIR_SHARE_ESTIMATE)
    main_calls = main_calls_per_case * len(billable)
    critic_calls = self_check_share * len(billable)
    main_prompt_tokens = sum(
        estimate_prompt_tokens(str(case.get("text", "")), spec7.TRIAGE_SYSTEM_PROMPT)
        for case in billable
    ) * main_calls_per_case
    critic_prompt_tokens = sum(
        estimate_prompt_tokens(str(case.get("text", "")), CRITIC_PROMPT_TEXT)
        for case in billable
    ) * self_check_share
    main_completion_tokens = main_calls * max_tokens_for(main["location"])
    critic_completion_tokens = critic_calls * max_tokens_for(critic["location"])
    main_cost = estimated_cost(main_prompt_tokens, main_completion_tokens, main)
    critic_cost = estimated_cost(critic_prompt_tokens, critic_completion_tokens, critic)
    return {
        "mode": mode,
        "cases": len(cases),
        "rejected_by_input": len(cases) - len(billable),
        "self_check_share": self_check_share,
        "calls": int(round(main_calls + critic_calls)),
        "prompt_tokens": int(main_prompt_tokens + critic_prompt_tokens),
        "completion_tokens": int(main_completion_tokens + critic_completion_tokens),
        "cost_usd": round(main_cost + critic_cost, 8),
        "main_calls": int(round(main_calls)),
        "main_prompt_tokens": int(main_prompt_tokens),
        "main_completion_tokens": int(main_completion_tokens),
        "main_cost_usd": main_cost,
        "critic_calls": int(round(critic_calls)),
        "critic_prompt_tokens": int(critic_prompt_tokens),
        "critic_completion_tokens": int(critic_completion_tokens),
        "critic_cost_usd": critic_cost,
    }


def write_line(label: str, value: str) -> None:
    sys.stdout.write("%-18s%s\n" % (label + ":", value))


def print_price_lines(price_label: str, source_label: str, endpoint: Dict[str, str]) -> None:
    if endpoint["location"] == spec7.LOCATION_LOCAL:
        write_line(price_label, "локальный инференс, деньги не тратятся")
        return
    price = llm_client.resolve_price(endpoint["model"])
    if price["source"] == spec7.PRICE_SOURCE_UNKNOWN:
        write_line(
            price_label,
            "не подтверждена, модели %s нет в таблице цен - стоимость считаться не будет"
            % endpoint["model"],
        )
        return
    write_line(
        price_label,
        "вход %.3f, кэш-вход %.4f, выход %.3f USD за 1M токенов"
        % (price["input"], price["cached_input"], price["output"]),
    )
    write_line(
        source_label,
        "%s, тариф %s, %s" % (price["source"], price["resolved_as"], price["source_url"]),
    )


def describe_thinking(location: str, thinking: bool) -> str:
    if location == spec7.LOCATION_LOCAL and not thinking:
        return "выключено"
    return "как у модели по умолчанию"


def describe_estimated_cost(endpoint: Dict[str, str], cost: float) -> str:
    if endpoint["location"] == spec7.LOCATION_LOCAL:
        return "локально, денег не стоит"
    if not llm_client.price_is_known(endpoint["model"]):
        return "цена не подтверждена"
    return "%.4f USD" % cost


def print_cost_split(
    estimates: List[Dict[str, Any]], main: Dict[str, str], critic: Dict[str, str]
) -> None:
    rows = (
        ("основной проход", main, "main_calls", "main_prompt_tokens", "main_completion_tokens", "main_cost_usd"),
        ("критик", critic, "critic_calls", "critic_prompt_tokens", "critic_completion_tokens", "critic_cost_usd"),
    )
    sys.stdout.write("Раздельно по моделям, каждая по своей цене:\n")
    for title, endpoint, calls_key, prompt_key, completion_key, cost_key in rows:
        calls = sum(estimate[calls_key] for estimate in estimates)
        prompt_tokens = sum(estimate[prompt_key] for estimate in estimates)
        completion_tokens = sum(estimate[completion_key] for estimate in estimates)
        cost = sum(estimate[cost_key] for estimate in estimates)
        sys.stdout.write(
            "  %-16s %-16s вызовов %-6d вход %-8d выход %-8d %s\n"
            % (
                title,
                endpoint["model"],
                calls,
                prompt_tokens,
                completion_tokens,
                describe_estimated_cost(endpoint, cost),
            )
        )


def print_dry_run(
    args: argparse.Namespace,
    cases: List[Dict[str, Any]],
    cases_problem: Optional[str],
) -> None:
    main = main_endpoint(args)
    critic = critic_endpoint_of(args)
    critic_key_env = critic_endpoint(args)["key_env"]
    location = main["location"]
    trigger = resolve_trigger(args)
    sys.stdout.write("DRY-RUN: сеть не используется, ключ не требуется.\n")
    write_line("Файл кейсов", args.cases_path)
    write_line("Режим", args.mode)
    write_line("Модель", args.model)
    write_line("URL", "POST %s" % llm_client.completions_url(args.base_url))
    write_line("Инференс", location)
    write_line("Переменная ключа", args.key_env)
    write_line("Ключ", describe_key_for(location, args.key_env))
    write_line("Адаптер", describe_adapter(args.adapters))
    print_price_lines("Цена модели", "Источник цены", main)
    write_line("Критик", describe_critic_endpoint(args))
    write_line("Адаптер критика", describe_adapter(critic_endpoint(args)["adapters"]))
    write_line("URL критика", "POST %s" % llm_client.completions_url(critic["base_url"]))
    write_line("Инференс критика", critic["location"])
    write_line(
        "Ключ критика",
        "%s - %s" % (critic_key_env, describe_key_for(critic["location"], critic_key_env)),
    )
    print_price_lines("Цена критика", "Тариф критика", critic)
    write_line("Таймаут", "%d с" % args.timeout)
    write_line("Параллельно", "%d кейсов" % args.workers)
    write_line("Триггер критика", "%s - %s" % (trigger, spec7.SELF_CHECK_TRIGGER_TITLES[trigger]))
    write_line(
        "Температуры",
        "baseline %.1f, redundancy %.1f, self-check %.1f"
        % (spec7.TEMPERATURE_BASELINE, spec7.TEMPERATURE_REDUNDANCY, spec7.TEMPERATURE_SELF_CHECK),
    )
    write_line(
        "max_tokens",
        "%d у основной модели, %d у критика"
        % (max_tokens_for(location), max_tokens_for(critic["location"])),
    )
    write_line(
        "Размышление",
        "основная - %s, критик - %s"
        % (
            describe_thinking(location, args.thinking),
            describe_thinking(critic["location"], args.thinking),
        ),
    )
    for mode in modes_for(args.mode):
        sys.stdout.write(
            "Вывод %-9s %s\n" % (mode + ":", out_path_for(args.out_dir, mode, args.out_suffix))
        )
    if cases_problem is not None:
        sys.stdout.write("\nКейсы прочитать не удалось: %s\n" % cases_problem)
        sys.stdout.write("Запросов было бы отправлено: 0.\n")
        return
    rejected = [case for case in cases if not guards.check_input(str(case.get("text", ""))).ok]
    sys.stdout.write("\nКейсов к прогону: %d\n" % len(cases))
    sys.stdout.write(
        "Отсекается предусловием входа: %d (%s)\n"
        % (len(rejected), ", ".join(str(case.get("id")) for case in rejected) or "нет")
    )
    with_markers = [case for case in cases if markers_of(case)]
    sys.stdout.write(
        "Кейсов с признаком риска: %d из %d (%d%%)\n"
        % (
            len(with_markers),
            len(cases),
            int(round(risk_share(cases) * 100)),
        )
    )
    groups = risk_by_group(cases)
    sys.stdout.write(
        "  по группам: %s\n"
        % ", ".join(
            "%s %d/%d" % (name, groups[name][0], groups[name][1])
            for name in list(spec7.GROUPS) + sorted(set(groups) - set(spec7.GROUPS))
            if name in groups
        )
    )
    labels = risk_by_label(cases)
    sys.stdout.write(
        "  по признакам: %s\n"
        % (
            ", ".join(
                "%s %d" % (label, labels[label]) for label in spec7.RISK_LABELS if label in labels
            )
            or "ни один не сработал"
        )
    )
    sys.stdout.write(
        "\n%-10s %-9s %-11s %-8s %-16s %-18s %s\n"
        % ("режим", "отказов", "self-check", "вызовов", "токенов вход", "токенов выход", "оценка стоимости")
    )
    total_calls = 0
    total_cost = 0.0
    estimates = []
    for mode in modes_for(args.mode):
        estimate = estimate_mode(cases, mode, main, critic, trigger)
        estimates.append(estimate)
        total_calls += estimate["calls"]
        total_cost += estimate["cost_usd"]
        sys.stdout.write(
            "%-10s %-9d %-11s %-8d %-16d %-18d %.4f USD\n"
            % (
                estimate["mode"],
                estimate["rejected_by_input"],
                "%d%%" % int(round(estimate["self_check_share"] * 100)),
                estimate["calls"],
                estimate["prompt_tokens"],
                estimate["completion_tokens"],
                estimate["cost_usd"],
            )
        )
    sys.stdout.write("\nВсего вызовов: %d, оценка сверху: %.4f USD.\n" % (total_calls, total_cost))
    print_cost_split(estimates, main, critic)
    billable = [case for case in cases if guards.check_input(str(case.get("text", ""))).ok]
    sys.stdout.write(
        "Оценка грубая: выход считается по max_tokens, доля ремонтных вызовов взята как %.0f%%.\n"
        % (REPAIR_SHARE_ESTIMATE * 100)
    )
    sys.stdout.write(
        "%s\n" % describe_self_check_share(trigger, self_check_share_for(trigger, billable))
    )


def run_one(
    case: Dict[str, Any],
    mode: str,
    client_cfg: llm_client.ClientConfig,
    trigger: str = spec7.SELF_CHECK_TRIGGER_AGREEMENT,
    critic_cfg: Optional[llm_client.ClientConfig] = None,
) -> pipeline.Decision:
    case_id = str(case.get("id"))
    case_text = str(case.get("text", ""))
    try:
        if mode == spec7.MODE_BASELINE:
            return pipeline.run_baseline(case_text, client_cfg, case_id)
        return pipeline.run_pipeline(case_text, client_cfg, case_id, trigger, critic_cfg)
    except Exception as unexpected_error:
        return pipeline.failed_decision(
            case_id, mode, "сбой прогона кейса: %s" % unexpected_error, client_cfg, critic_cfg
        )


def describe_key_for(location: str, key_env: str) -> str:
    if location == spec7.LOCATION_LOCAL:
        return "не требуется, заголовок Authorization не отправляется"
    return llm_client.describe_key_source(key_env)


def preview_of(case: Dict[str, Any]) -> str:
    text = " ".join(str(case.get("text", "")).split())
    if len(text) <= PROGRESS_PREVIEW_CHARS:
        return text
    return text[:PROGRESS_PREVIEW_CHARS] + "..."


def run_mode(
    cases: List[Dict[str, Any]],
    mode: str,
    client_cfg: llm_client.ClientConfig,
    out_dir: str,
    workers: int,
    suffix: str = "",
    trigger: str = spec7.SELF_CHECK_TRIGGER_AGREEMENT,
    critic_cfg: Optional[llm_client.ClientConfig] = None,
) -> Dict[str, Any]:
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    out_path = out_path_for(out_dir, mode, suffix)
    decisions: Dict[int, pipeline.Decision] = {}
    lock = threading.Lock()
    done = 0
    started = time.time()

    sys.stdout.write("\nРежим %s: кейсов %d, потоков %d\n" % (mode, len(cases), workers))
    sys.stdout.write("Вывод: %s\n" % out_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(run_one, case, mode, client_cfg, trigger, critic_cfg): position
            for position, case in enumerate(cases)
        }
        for future in concurrent.futures.as_completed(futures):
            position = futures[future]
            decision = future.result()
            with lock:
                decisions[position] = decision
                done += 1
                sys.stdout.write(
                    "  [%d/%d] %-14s %-12s %-7s вызовов %d, %d мс  %s\n"
                    % (
                        done,
                        len(cases),
                        decision.case_id,
                        decision.route or "-",
                        decision.status,
                        decision.calls,
                        decision.latency_ms,
                        ("ошибка: " + decision.error[:60]) if decision.error else preview_of(cases[position]),
                    )
                )
                sys.stdout.flush()

    ordered = [decisions[position] for position in sorted(decisions)]
    with open(out_path, "w", encoding="utf-8") as handle:
        for decision in ordered:
            handle.write(json.dumps(dataclasses.asdict(decision), ensure_ascii=False) + "\n")

    failed = sum(1 for decision in ordered if decision.error)
    total_cost = sum(decision.cost_usd for decision in ordered)
    total_calls = sum(decision.calls for decision in ordered)
    elapsed = time.time() - started
    sys.stdout.write(
        "Режим %s готов: кейсов %d, с ошибкой %d, вызовов %d, стоимость %.4f USD, время %.1f с\n"
        % (mode, len(ordered), failed, total_calls, total_cost, elapsed)
    )
    return {"mode": mode, "cases": len(ordered), "failed": failed, "out_path": out_path}


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.workers <= 0:
        sys.stderr.write("Значение --workers должно быть больше нуля.\n")
        return EXIT_CONFIG_ERROR
    if args.limit < 0:
        sys.stderr.write("Значение --limit не может быть отрицательным.\n")
        return EXIT_CONFIG_ERROR

    cases: List[Dict[str, Any]] = []
    cases_problem: Optional[str] = None
    try:
        cases = load_cases(args.cases_path, args.limit)
    except CasesError as cases_error:
        cases_problem = str(cases_error)
    except OSError as os_error:
        cases_problem = "не читается %s: %s" % (args.cases_path, os_error)

    if args.dry_run:
        print_dry_run(args, cases, cases_problem)
        return EXIT_OK

    if cases_problem is not None:
        sys.stderr.write("Не могу прочитать кейсы: %s\n" % cases_problem)
        return EXIT_DATA_ERROR

    location = llm_client.inference_location(args.base_url)
    api_key = "" if location == spec7.LOCATION_LOCAL else llm_client.read_api_key(args.key_env)
    if location == spec7.LOCATION_CLOUD and not api_key:
        sys.stderr.write(
            "Ключ %s не найден ни в окружении, ни в %s. "
            "Экспортируйте переменную окружения и повторите: export %s=<ваш ключ>\n"
            % (args.key_env, spec7.LOCAL_PROPERTIES_PATH, args.key_env)
        )
        return EXIT_CONFIG_ERROR

    thinking_off = location == spec7.LOCATION_LOCAL and not args.thinking
    client_cfg = llm_client.ClientConfig(
        model=args.model,
        base_url=args.base_url,
        api_key=api_key,
        timeout=args.timeout,
        extra_payload=build_extra_payload(thinking_off, args.adapters),
    )
    sys.stdout.write(
        "Модель: %s, инференс: %s, ключ: %s, таймаут: %d с\n"
        % (args.model, location, describe_key_for(location, args.key_env), args.timeout)
    )
    sys.stdout.write("Адаптер: %s\n" % describe_adapter(client_cfg.adapter))
    warn_missing_adapter("основной модели", client_cfg.adapter)
    sys.stdout.write(
        "max_tokens: %d, размышление модели: %s\n"
        % (client_cfg.max_tokens, "выключено" if thinking_off else "как у модели по умолчанию")
    )
    critic_cfg, critic_problem = build_critic_config(args)
    if critic_problem is not None:
        sys.stderr.write(critic_problem + "\n")
        return EXIT_CONFIG_ERROR
    sys.stdout.write("Критик: %s\n" % describe_critic_endpoint(args))
    critic_adapter = critic_cfg.adapter if critic_cfg is not None else client_cfg.adapter
    sys.stdout.write("Адаптер критика: %s\n" % describe_adapter(critic_adapter))
    warn_missing_adapter("критика", critic_adapter)
    if critic_cfg is not None:
        sys.stdout.write(
            "Критик, инференс: %s, ключ: %s\n"
            % (
                critic_cfg.location,
                describe_key_for(critic_cfg.location, critic_endpoint(args)["key_env"]),
            )
        )
    warn_shared_key_env(args)
    trigger = resolve_trigger(args)
    sys.stdout.write(
        "Триггер критика: %s - %s\n" % (trigger, spec7.SELF_CHECK_TRIGGER_TITLES[trigger])
    )
    if trigger == spec7.SELF_CHECK_TRIGGER_RISK:
        sys.stdout.write(
            "Кейсов с признаком риска: %d из %d\n"
            % (sum(1 for case in cases if markers_of(case)), len(cases))
        )

    summaries = [
        run_mode(
            cases, mode, client_cfg, args.out_dir, args.workers, args.out_suffix, trigger,
            critic_cfg,
        )
        for mode in modes_for(args.mode)
    ]
    total_failed = sum(summary["failed"] for summary in summaries)
    sys.stdout.write("\nГотово. Кейсов с ошибкой суммарно: %d\n" % total_failed)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
