"""Тонкий клиент chat/completions на стандартной библиотеке.

Ключ читается из окружения либо из local.properties и никогда не печатается:
в любом выводе на его месте стоит маркер ***.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import spec7

MASKED_KEY = "***"
RETRYABLE_STATUS = 429
SERVER_ERROR_FLOOR = 500
ERROR_BODY_CHARS = 300
COMMENT_PREFIXES = ("#", "!")


@dataclass
class CallResult:
    content: str
    usage: Dict[str, Any]
    latency_ms: int
    error: Optional[str]
    status_code: Optional[int]


@dataclass
class ClientConfig:
    model: str = spec7.DEFAULT_MODEL
    base_url: str = spec7.DEFAULT_BASE_URL
    api_key: str = ""
    timeout: int = spec7.REQUEST_TIMEOUT_SECONDS
    extra_payload: Optional[Dict[str, Any]] = None

    @property
    def location(self) -> str:
        return inference_location(self.base_url)

    @property
    def is_local(self) -> bool:
        return self.location == spec7.LOCATION_LOCAL

    @property
    def adapter(self) -> str:
        if not self.extra_payload:
            return ""
        value = self.extra_payload.get(spec7.ADAPTERS_PAYLOAD_KEY)
        if not isinstance(value, str):
            return ""
        return value

    @property
    def max_tokens(self) -> int:
        if self.is_local:
            return spec7.LOCAL_MAX_TOKENS
        return spec7.MAX_TOKENS


def inference_location(base_url: str) -> str:
    host = urllib.parse.urlparse(base_url).hostname or ""
    if host.lower() in spec7.LOCAL_HOSTS:
        return spec7.LOCATION_LOCAL
    return spec7.LOCATION_CLOUD


def read_api_key(env_name: str = spec7.DEFAULT_KEY_ENV) -> str:
    from_environment = os.environ.get(env_name, "").strip()
    if from_environment:
        return from_environment
    return read_key_from_local_properties(env_name, spec7.LOCAL_PROPERTIES_PATH)


def read_key_from_local_properties(env_name: str, path: str) -> str:
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return ""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_PREFIXES):
            continue
        if "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        if name.strip() != env_name:
            continue
        return value.strip().strip('"').strip("'")
    return ""


def describe_key_source(env_name: str = spec7.DEFAULT_KEY_ENV) -> str:
    if os.environ.get(env_name, "").strip():
        return "переменная окружения %s (значение %s)" % (env_name, MASKED_KEY)
    if read_key_from_local_properties(env_name, spec7.LOCAL_PROPERTIES_PATH):
        return "local.properties, ключ %s (значение %s)" % (env_name, MASKED_KEY)
    return "не найден ни в окружении, ни в local.properties"


def completions_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/chat/completions"


def build_payload(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    model: str,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra_payload:
        payload.update(extra_payload)
    return payload


def send_once(url: str, body: bytes, api_key: str, timeout: int) -> Tuple[int, str]:
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if api_key:
        request.add_header("Authorization", "Bearer " + api_key)
    response = urllib.request.urlopen(request, timeout=timeout)
    try:
        return response.getcode(), response.read().decode("utf-8", "replace")
    finally:
        response.close()


def is_retryable_status(status: int) -> bool:
    return status == RETRYABLE_STATUS or status >= SERVER_ERROR_FLOOR


def send_with_retries(
    url: str,
    body: bytes,
    api_key: str,
    timeout: int,
) -> Tuple[Optional[int], str, Optional[str]]:
    attempt = 0
    last_status: Optional[int] = None
    last_error = "неизвестная ошибка"
    while attempt <= len(spec7.RETRY_DELAYS_SECONDS):
        try:
            status, raw_body = send_once(url, body, api_key, timeout)
            return status, raw_body, None
        except urllib.error.HTTPError as http_error:
            last_status = http_error.code
            last_error = "HTTP %d: %s" % (http_error.code, read_error_body(http_error))
            if not is_retryable_status(http_error.code):
                return last_status, "", last_error
        except urllib.error.URLError as url_error:
            last_status = None
            last_error = "сетевая ошибка: %s" % url_error.reason
        except Exception as unexpected_error:
            last_status = None
            last_error = "ошибка запроса: %s" % unexpected_error
        if attempt == len(spec7.RETRY_DELAYS_SECONDS):
            break
        time.sleep(spec7.RETRY_DELAYS_SECONDS[attempt])
        attempt += 1
    return last_status, "", last_error


def read_error_body(http_error: urllib.error.HTTPError) -> str:
    try:
        return http_error.read().decode("utf-8", "replace")[:ERROR_BODY_CHARS]
    except Exception:
        return ""


def parse_completion(raw_body: str) -> Tuple[str, Dict[str, Any], Optional[str]]:
    try:
        parsed = json.loads(raw_body)
    except ValueError as parse_error:
        return "", {}, "ответ не парсится как JSON: %s" % parse_error
    if not isinstance(parsed, dict):
        return "", {}, "ответ не объект JSON"
    usage = parsed.get("usage") or {}
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        return "", usage, "в ответе нет choices"
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        return "", usage, describe_missing_content(choices[0], message)
    return content, usage, None


def describe_missing_content(choice: Dict[str, Any], message: Dict[str, Any]) -> str:
    reasoning = message.get("reasoning")
    finish_reason = choice.get("finish_reason")
    if isinstance(reasoning, str) and reasoning:
        return (
            "в ответе нет message.content, модель вернула только блок reasoning на %d символов, "
            "finish_reason=%s" % (len(reasoning), finish_reason)
        )
    return "в ответе нет message.content, finish_reason=%s" % finish_reason


def call_model(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    model: str,
    base_url: str,
    api_key: str,
    timeout: int = spec7.REQUEST_TIMEOUT_SECONDS,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> CallResult:
    url = completions_url(base_url)
    body = json.dumps(
        build_payload(messages, temperature, max_tokens, model, extra_payload), ensure_ascii=False
    ).encode("utf-8")
    started = time.time()
    status, raw_body, transport_error = send_with_retries(url, body, api_key, timeout)
    if transport_error is not None:
        latency_ms = int((time.time() - started) * 1000)
        return CallResult("", {}, latency_ms, transport_error, status)
    content, usage, parse_error = parse_completion(raw_body)
    latency_ms = int((time.time() - started) * 1000)
    return CallResult(content, usage, latency_ms, parse_error, status)


def call_with_config(
    messages: List[Dict[str, str]],
    temperature: float,
    config: ClientConfig,
    max_tokens: Optional[int] = None,
) -> CallResult:
    if max_tokens is None:
        max_tokens = config.max_tokens
    if config.extra_payload:
        return call_model(
            messages,
            temperature,
            max_tokens,
            config.model,
            config.base_url,
            config.api_key,
            config.timeout,
            config.extra_payload,
        )
    return call_model(
        messages,
        temperature,
        max_tokens,
        config.model,
        config.base_url,
        config.api_key,
        config.timeout,
    )


def token_count(usage: Dict[str, Any], key: str) -> int:
    value = usage.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    if value < 0:
        return 0
    return value


def resolve_price(model: str) -> Dict[str, Any]:
    name = (model or "").strip()
    if name in spec7.PRICES:
        return spec7.PRICES[name]
    matches = [key for key in spec7.PRICES if name.startswith(key)]
    if not matches:
        return spec7.PRICE_UNKNOWN
    return spec7.PRICES[max(matches, key=len)]


def price_source(model: str) -> str:
    return resolve_price(model)["source"]


def price_is_known(model: str) -> bool:
    return price_source(model) == spec7.PRICE_SOURCE_CONFIRMED


def cached_token_count(usage: Dict[str, Any]) -> int:
    direct = token_count(usage, spec7.CACHED_TOKEN_KEY)
    if direct:
        return direct
    details = usage.get(spec7.OPENAI_TOKEN_DETAILS_KEY)
    if isinstance(details, dict):
        return token_count(details, spec7.OPENAI_CACHED_TOKEN_KEY)
    return 0


def usage_cost(usage: Dict[str, Any], model: str) -> float:
    if not isinstance(usage, dict):
        return 0.0
    price = resolve_price(model)
    if price["source"] == spec7.PRICE_SOURCE_UNKNOWN:
        return 0.0
    prompt_tokens = token_count(usage, "prompt_tokens")
    completion_tokens = token_count(usage, "completion_tokens")
    cached_tokens = min(cached_token_count(usage), prompt_tokens)
    fresh_tokens = max(prompt_tokens - cached_tokens, 0)
    input_cost = fresh_tokens * price["input"] / spec7.TOKENS_PER_MILLION
    cached_cost = cached_tokens * price["cached_input"] / spec7.TOKENS_PER_MILLION
    output_cost = completion_tokens * price["output"] / spec7.TOKENS_PER_MILLION
    return round(input_cost + cached_cost + output_cost, 8)


def merge_usage(total: Dict[str, int], usage: Dict[str, Any]) -> Dict[str, int]:
    merged = dict(total)
    for key in ("prompt_tokens", "completion_tokens"):
        merged[key] = merged.get(key, 0) + token_count(usage, key)
    merged[spec7.CACHED_TOKEN_KEY] = merged.get(spec7.CACHED_TOKEN_KEY, 0) + cached_token_count(usage)
    merged["total_tokens"] = merged["prompt_tokens"] + merged["completion_tokens"]
    return merged


def empty_usage() -> Dict[str, int]:
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
