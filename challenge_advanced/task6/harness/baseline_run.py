# -*- coding: utf-8 -*-
"""
Baseline-прогон ассистента ALVA без файнтюна.

Берёт первые N примеров из artifacts/eval.jsonl, отправляет в базовую модель только system и user
(эталонный assistant в запрос не идёт) и складывает ответы в raw/baseline_responses_<provider>.jsonl.
Это точка отсчёта, с которой потом сравнивается дообученная модель.

Ключ читается только из переменной окружения провайдера и никогда не печатается.
Режим --dry-run сеть не трогает и ключа не требует.

Провайдеры: openrouter (по умолчанию, даёт доступ к gpt-4o-mini), openai, deepseek.

Запуск: python3 harness/baseline_run.py --dry-run
        python3 harness/baseline_run.py --provider openrouter --n 10
        python3 harness/baseline_run.py --provider openai --model gpt-4o-mini --n 10
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

try:
    from spec import ARTIFACTS_DIR, RAW_DIR, SYSTEM_PROMPT
except ImportError as import_error:
    sys.stderr.write(
        "Не найден модуль harness/spec.py (он держит SYSTEM_PROMPT и пути). "
        "Соберите харнесс полностью и повторите. Причина: %s\n" % import_error
    )
    sys.exit(2)

PROVIDER_PROFILES = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "key_env": "OPENROUTER_API_KEY",
        "supports_seed": True,
        "extra_headers": {
            "HTTP-Referer": "https://github.com/local/alva-task6",
            "X-Title": "ALVA task6 baseline",
        },
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-v4-flash",
        "key_env": "DEEPSEEK_API_KEY",
        "supports_seed": False,
        "extra_headers": {},
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
        "supports_seed": True,
        "extra_headers": {},
    },
}

DEFAULT_PROVIDER = "openrouter"
DEFAULT_EXAMPLES = 10
REQUEST_TIMEOUT_SECONDS = 90
RETRY_DELAYS_SECONDS = (2, 5, 15, 40)
RETRYABLE_STATUS = 429
SERVER_ERROR_FLOOR = 500
TEMPERATURE = 0
MAX_TOKENS = 900
FIXED_SEED = 7
MASKED_AUTHORIZATION = "Authorization: Bearer ***"
EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_CONFIG_ERROR = 2

EVAL_FILE_NAME = "eval.jsonl"
OUTPUT_TEMPLATE = "baseline_responses_%s.jsonl"


class EvalDatasetError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Прогон baseline по eval.jsonl без файнтюна.",
    )
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDER_PROFILES.keys()),
        default=DEFAULT_PROVIDER,
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--n", type=int, default=DEFAULT_EXAMPLES)
    parser.add_argument("--eval", dest="eval_path", default=None)
    parser.add_argument("--out", dest="out_path", default=None)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    return parser


def resolve_eval_path(raw_value: Optional[str]) -> str:
    if raw_value:
        return os.path.abspath(raw_value)
    return os.path.join(ARTIFACTS_DIR, EVAL_FILE_NAME)


def resolve_out_path(raw_value: Optional[str], provider: str) -> str:
    if raw_value:
        return os.path.abspath(raw_value)
    return os.path.join(RAW_DIR, OUTPUT_TEMPLATE % provider)


def extract_role(messages: List[Dict[str, Any]], role: str) -> Optional[str]:
    for message in messages:
        if isinstance(message, dict) and message.get("role") == role:
            content = message.get("content")
            if isinstance(content, str):
                return content
    return None


def load_eval_examples(eval_path: str, limit: int) -> List[Dict[str, Any]]:
    examples = []
    with open(eval_path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except ValueError as parse_error:
                raise EvalDatasetError(
                    "Строка %d в %s не парсится как JSON: %s"
                    % (line_number, eval_path, parse_error)
                )
            messages = record.get("messages")
            if not isinstance(messages, list) or not messages:
                raise EvalDatasetError(
                    "Строка %d в %s без ключа messages" % (line_number, eval_path)
                )
            user_text = extract_role(messages, "user")
            if user_text is None:
                raise EvalDatasetError(
                    "Строка %d в %s без роли user" % (line_number, eval_path)
                )
            system_text = extract_role(messages, "system")
            if system_text is None:
                system_text = SYSTEM_PROMPT
            examples.append(
                {
                    "index": len(examples),
                    "system": system_text,
                    "user": user_text,
                    "reference": extract_role(messages, "assistant") or "",
                }
            )
            if len(examples) >= limit:
                break
    return examples


def build_payload(model: str, example: Dict[str, Any], supports_seed: bool) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": example["system"]},
            {"role": "user", "content": example["user"]},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }
    if supports_seed:
        payload["seed"] = FIXED_SEED
    return payload


def encode_payload(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def send_once(
    url: str,
    body: bytes,
    api_key: str,
    extra_headers: Dict[str, str],
) -> Tuple[int, str]:
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", "Bearer " + api_key)
    for header_name, header_value in extra_headers.items():
        request.add_header(header_name, header_value)
    response = urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        raw_body = response.read().decode("utf-8", "replace")
        return response.getcode(), raw_body
    finally:
        response.close()


def is_retryable_status(status: int) -> bool:
    return status == RETRYABLE_STATUS or status >= SERVER_ERROR_FLOOR


def send_with_retries(
    url: str,
    body: bytes,
    api_key: str,
    extra_headers: Dict[str, str],
) -> Tuple[Optional[int], str, Optional[str]]:
    attempt = 0
    last_error = "неизвестная ошибка"
    last_status = None
    while attempt <= len(RETRY_DELAYS_SECONDS):
        try:
            status, raw_body = send_once(url, body, api_key, extra_headers)
            return status, raw_body, None
        except urllib.error.HTTPError as http_error:
            last_status = http_error.code
            try:
                error_body = http_error.read().decode("utf-8", "replace")
            except Exception:
                error_body = ""
            last_error = "HTTP %d: %s" % (http_error.code, error_body[:300])
            if not is_retryable_status(http_error.code):
                return last_status, "", last_error
        except urllib.error.URLError as url_error:
            last_status = None
            last_error = "сетевая ошибка: %s" % url_error.reason
        except Exception as unexpected_error:
            last_status = None
            last_error = "ошибка запроса: %s" % unexpected_error
        if attempt == len(RETRY_DELAYS_SECONDS):
            break
        delay = RETRY_DELAYS_SECONDS[attempt]
        sys.stdout.write(
            "  повтор через %d с (попытка %d): %s\n" % (delay, attempt + 2, last_error)
        )
        sys.stdout.flush()
        time.sleep(delay)
        attempt += 1
    return last_status, "", last_error


def parse_completion(raw_body: str) -> Tuple[str, Dict[str, Any], Optional[str]]:
    try:
        parsed = json.loads(raw_body)
    except ValueError as parse_error:
        return "", {}, "ответ не парсится как JSON: %s" % parse_error
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        return "", parsed.get("usage") or {}, "в ответе нет choices"
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        return "", parsed.get("usage") or {}, "в ответе нет message.content"
    return content, parsed.get("usage") or {}, None


def describe_headers(profile: Dict[str, Any]) -> str:
    parts = ["Content-Type: application/json", MASKED_AUTHORIZATION]
    for header_name, header_value in profile["extra_headers"].items():
        parts.append("%s: %s" % (header_name, header_value))
    return ", ".join(parts)


def print_dry_run(
    provider: str,
    profile: Dict[str, Any],
    model: str,
    url: str,
    eval_path: str,
    out_path: str,
    examples: List[Dict[str, Any]],
    requested: int,
    eval_problem: Optional[str],
) -> None:
    sys.stdout.write("DRY-RUN: сеть не используется, ключ не требуется.\n")
    sys.stdout.write("Провайдер:        %s\n" % provider)
    sys.stdout.write("URL:              POST %s\n" % url)
    sys.stdout.write("Заголовки:        %s\n" % describe_headers(profile))
    sys.stdout.write("Ключ из env:      %s (значение не печатается)\n" % profile["key_env"])
    sys.stdout.write("Модель:           %s\n" % model)
    sys.stdout.write("temperature:      %s\n" % TEMPERATURE)
    sys.stdout.write("max_tokens:       %s\n" % MAX_TOKENS)
    sys.stdout.write(
        "seed:             %s\n"
        % (str(FIXED_SEED) if profile["supports_seed"] else "не отправляется (провайдер может не знать параметр)")
    )
    sys.stdout.write("Таймаут:          %d с\n" % REQUEST_TIMEOUT_SECONDS)
    sys.stdout.write(
        "Ретраи:           паузы %s с на 429 и 5xx\n"
        % ", ".join(str(delay) for delay in RETRY_DELAYS_SECONDS)
    )
    sys.stdout.write("Файл eval:        %s\n" % eval_path)
    sys.stdout.write("Файл вывода:      %s\n" % out_path)
    if eval_problem is not None:
        sys.stdout.write("\nПримеры прочитать не удалось: %s\n" % eval_problem)
        sys.stdout.write("Запросов было бы отправлено: 0 (нужен собранный artifacts/eval.jsonl).\n")
        return
    sys.stdout.write("Запрошено примеров: %d, доступно: %d\n" % (requested, len(examples)))
    sys.stdout.write("\nПлан запросов:\n")
    sys.stdout.write("%-5s %-12s %-12s %s\n" % ("idx", "body_bytes", "user_chars", "начало реплики"))
    total_bytes = 0
    for example in examples:
        body = encode_payload(build_payload(model, example, profile["supports_seed"]))
        total_bytes += len(body)
        preview = example["user"].replace("\n", " ")[:48]
        sys.stdout.write(
            "%-5d %-12d %-12d %s\n" % (example["index"], len(body), len(example["user"]), preview)
        )
    sys.stdout.write("\nВсего запросов: %d, суммарный размер тел: %d байт.\n" % (len(examples), total_bytes))


def run_live(
    profile: Dict[str, Any],
    model: str,
    url: str,
    provider: str,
    api_key: str,
    examples: List[Dict[str, Any]],
    out_path: str,
) -> int:
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    succeeded = 0
    failed = 0
    sys.stdout.write("Провайдер: %s, модель: %s, примеров: %d\n" % (provider, model, len(examples)))
    sys.stdout.write("Вывод: %s\n\n" % out_path)
    sys.stdout.write(
        "%-5s %-12s %-22s %-8s %-12s %s\n"
        % ("idx", "provider", "model", "chars", "latency_ms", "статус")
    )
    with open(out_path, "w", encoding="utf-8") as handle:
        for example in examples:
            payload = build_payload(model, example, profile["supports_seed"])
            body = encode_payload(payload)
            started = time.time()
            status, raw_body, transport_error = send_with_retries(
                url, body, api_key, profile["extra_headers"]
            )
            latency_ms = int((time.time() - started) * 1000)
            response_text = ""
            usage = {}
            error_text = transport_error
            if transport_error is None:
                response_text, usage, parse_error = parse_completion(raw_body)
                error_text = parse_error
            if error_text is None:
                succeeded += 1
                status_label = "ok"
            else:
                failed += 1
                status_label = "ошибка: %s" % error_text[:80]
            record = {
                "index": example["index"],
                "provider": provider,
                "model": model,
                "user": example["user"],
                "reference": example["reference"],
                "response": response_text,
                "latency_ms": latency_ms,
                "usage": usage,
                "error": error_text,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            sys.stdout.write(
                "%-5d %-12s %-22s %-8d %-12d %s\n"
                % (
                    example["index"],
                    provider,
                    model[:22],
                    len(response_text),
                    latency_ms,
                    status_label,
                )
            )
            sys.stdout.flush()
    sys.stdout.write("\nУспешно: %d, с ошибкой: %d, всего: %d\n" % (succeeded, failed, len(examples)))
    sys.stdout.write("Ответы записаны в %s\n" % out_path)
    return EXIT_OK if failed == 0 else EXIT_DATA_ERROR


def warn_system_drift(examples: List[Dict[str, Any]]) -> None:
    drifted = [example["index"] for example in examples if example["system"] != SYSTEM_PROMPT]
    if drifted:
        sys.stdout.write(
            "ВНИМАНИЕ: system в eval разъехался со spec.SYSTEM_PROMPT в строках %s. "
            "Сравнение с baseline будет нечестным.\n\n"
            % ", ".join(str(index) for index in drifted)
        )


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    profile = PROVIDER_PROFILES[args.provider]
    model = args.model or profile["model"]
    url = profile["base_url"].rstrip("/") + "/chat/completions"
    eval_path = resolve_eval_path(args.eval_path)
    out_path = resolve_out_path(args.out_path, args.provider)
    if args.n <= 0:
        sys.stderr.write("Значение --n должно быть больше нуля.\n")
        return EXIT_CONFIG_ERROR

    examples = []
    eval_problem = None
    if not os.path.isfile(eval_path):
        eval_problem = "файл %s ещё не собран (его делает build_dataset.py)" % eval_path
    else:
        try:
            examples = load_eval_examples(eval_path, args.n)
        except EvalDatasetError as dataset_error:
            eval_problem = str(dataset_error)
        except OSError as os_error:
            eval_problem = "не читается %s: %s" % (eval_path, os_error)
        if eval_problem is None and not examples:
            eval_problem = "файл %s пустой" % eval_path

    if args.dry_run:
        print_dry_run(
            args.provider, profile, model, url, eval_path, out_path, examples, args.n, eval_problem
        )
        return EXIT_OK

    if eval_problem is not None:
        sys.stderr.write("Не могу прочитать примеры: %s\n" % eval_problem)
        return EXIT_DATA_ERROR

    api_key = os.environ.get(profile["key_env"], "").strip()
    if not api_key:
        sys.stderr.write(
            "Не задана переменная окружения %s. Экспортируйте ключ провайдера и повторите: "
            "export %s=<ваш ключ>\n" % (profile["key_env"], profile["key_env"])
        )
        return EXIT_CONFIG_ERROR

    warn_system_drift(examples)
    if len(examples) < args.n:
        sys.stdout.write(
            "В eval нашлось только %d примеров из запрошенных %d.\n" % (len(examples), args.n)
        )
    return run_live(profile, model, url, args.provider, api_key, examples, out_path)


if __name__ == "__main__":
    sys.exit(main())
